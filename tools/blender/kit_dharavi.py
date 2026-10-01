"""
kit_dharavi.py - Dharavi (Mumbai slum) kit: one / two storey shanties, dense 3-4 storey self-built tenements,
corrugated-sheet shacks and walls, a concrete alley gateway, and street props (laundry lines, chai tapri,
snack strips, veg cart, matkas, recycling sacks, drums, LPG, cricket kit, stools, neon shop signs, tarp
canopies, tangled alley wires).

Conventions (as the rest of the kit): metres, Z up, +X along the street, building FRONT faces -Y, building
origin = bottom-centre of the front facade at street level. Props: origin bottom-centre unless noted.
Everything is seeded / deterministic.
"""
import math
import random
from mathutils import Vector, Matrix
from kit_core import MB, V, T, Rz, Rx, Ry, S, lerp
from kit_arch import (facade_wall, awning_corrugated, rolling_shutter, signboard, wire_hook, water_tank, antenna,
                      rebar_stubs)
from kit_buildings import PROF_BAND_SMALL
import kit_buildings as KB
from kit_arch import scaled_profile

# preview colours for the new slots (preview renders only; UE materials come from tools/ue/gi_common.py)
try:
    import kit_export as _KE
    _KE.PALETTE.update({
        'M_PlasterTeal': '#4FA59A', 'M_PlasterTurquoise': '#5BC2C4', 'M_PlasterBlueVivid': '#2F6FCC', 'M_PlasterCream': '#E4D6B0',
        'M_BrickExposed': '#9A6A4E', 'M_AsbestosRoof': '#9C9890', 'M_CorrugatedGalv': '#8C8D8A',
        'M_CorrugatedPainted': '#9A4A33', 'M_TinGreen': '#3F6A3A', 'M_TinBlue': '#2C4F75', 'M_ConcreteDirty': '#7F7A70',
        'M_TarpBlue': '#2050A8', 'M_PlasticBlue': '#1A4FB0', 'M_PlasticRed': '#C0201C', 'M_PlasticYellow': '#E8B020',
        'M_Terracotta': '#B05A32', 'M_ClayGreen': '#3C7A4A', 'M_TeaSteel': '#C8C8CC', 'M_Brass': '#D0A040',
        'M_Glass': '#A8B8B0', 'M_LPGRed': '#B01810', 'M_Rubber': '#202020', 'M_TennisYellow': '#D8E030',
        'M_BatWillow': '#D8B888', 'M_VegGreen': '#3C8A20', 'M_VegRed': '#D02818', 'M_Onion': '#B04858',
        'M_VegBrown': '#9A7040', 'M_Poster': '#D8C090',
        'M_SackWhite': '#E8E4D8', 'M_SackGreen': '#4C8A50', 'M_SackBlue': '#3A64B0', 'M_SackBeige': '#C8B088',
        'M_Snack_01': '#F05A10', 'M_Snack_02': '#F0C020', 'M_Snack_03': '#2060D0', 'M_Snack_04': '#30A040',
        'M_SnackFoil': '#D0D0D8',
        'M_LaundryRed': '#D02020', 'M_LaundryYellow': '#F0C818', 'M_LaundryPink': '#F060A0', 'M_LaundryGreen': '#30A040',
        'M_LaundryBlueL': '#70A8F0', 'M_LaundryWhite': '#F4F2EC', 'M_LaundryPurple': '#7A3AB0', 'M_LaundryOrange': '#F07818',
        'M_Neon_01': '#FF2080', 'M_Neon_02': '#20E0FF', 'M_Neon_03': '#FF3020', 'M_Neon_04': '#40FF60',
        'M_Neon_05': '#FFC020', 'M_Neon_06': '#F8F8FF',
    })
except Exception:
    pass

LAUNDRY = ['M_LaundryRed', 'M_LaundryYellow', 'M_LaundryPink', 'M_LaundryGreen', 'M_LaundryBlueL', 'M_LaundryWhite',
           'M_LaundryPurple', 'M_LaundryOrange']
SNACKS = ['M_Snack_01', 'M_Snack_02', 'M_Snack_03', 'M_Snack_04', 'M_SnackFoil']
ROOF_ASB = ['M_AsbestosRoof']
ROOF_TIN = ['M_CorrugatedRust', 'M_CorrugatedRust', 'M_CorrugatedGalv', 'M_CorrugatedPainted']
WALL_TIN = ['M_CorrugatedRust', 'M_CorrugatedGalv', 'M_CorrugatedPainted', 'M_CorrugatedRust', 'M_TinBlue', 'M_TinGreen']
DOOR_MATS = ['M_WoodShutter', 'M_TinBlue', 'M_TinGreen', 'M_WoodShutter', 'M_MetalRust']


# =========================================================================================== helpers
def dquad(mb, pts, mat, normal, th=0.006):
    """Double-sided thin face (cloth, tarp, posters)."""
    pts = [V(p) for p in pts]
    n = V(normal).normalized()
    mb.face(pts, mat, normal=n)
    mb.face([p - n * th for p in pts], mat, normal=-n)


def grid_faces(mb, rows, mat, normal, th=0.006, double=True):
    """rows[i][j] Vector grid -> quads (double-sided)."""
    n = V(normal).normalized()
    for i in range(len(rows) - 1):
        for j in range(len(rows[i]) - 1):
            q = [rows[i][j], rows[i + 1][j], rows[i + 1][j + 1], rows[i][j + 1]]
            mb.face(q, mat, normal=n)
            if double:
                mb.face([p - n * th for p in q], mat, normal=-n)


def corr_sheet(mb, O, U, Dv, w, L, mat, pitch=0.076, amp=0.016, under=None, th=0.008, nv=1, sag=0.0, N=None,
               rot=0.0):
    """Corrugated sheet. O = corner, U = across-rib axis (length w), Dv = along-rib axis (length L);
    profile offset along N (default U x Dv = visible side). under = material of the back side (None = single)."""
    O = V(O)
    U = V(U).normalized()
    Dv = V(Dv).normalized()
    Nn = U.cross(Dv).normalized() if N is None else V(N).normalized()
    if rot:
        R = Matrix.Rotation(rot, 3, Nn)
        U = R @ U
        Dv = R @ Dv
    k = max(2, int(round(w / (pitch / 4))))
    prof = (0.0, 1.0, 0.0, -1.0)
    us = [w * i / k for i in range(k + 1)]
    hs = [amp * prof[i % 4] for i in range(k + 1)]
    rows = []
    for j in range(nv + 1):
        t = j / nv
        rows.append([O + U * us[i] + Dv * (L * t) + Nn * (hs[i] - sag * math.sin(math.pi * t)) for i in range(k + 1)])
    for j in range(nv):
        for i in range(k):
            q = [rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]]
            mb.face(q, mat, normal=Nn)
            if under:
                mb.face([p - Nn * th for p in q], under, normal=-Nn)


def stone(mb, c, s, rng, mat='M_Concrete'):
    c = V(c)
    j = lambda: rng.uniform(0.7, 1.15)
    bot = [c + V(-s * j(), -s * j(), 0), c + V(s * j(), -s * j(), 0), c + V(s * j(), s * j(), 0), c + V(-s * j(), s * j(), 0)]
    h = s * rng.uniform(0.9, 1.4)
    top = [c + V(-s * j() * 0.6, -s * j() * 0.6, h), c + V(s * j() * 0.6, -s * j() * 0.6, h * j()),
           c + V(s * j() * 0.6, s * j() * 0.6, h), c + V(-s * j() * 0.6, s * j() * 0.6, h * j())]
    mb.hexa(bot, top, mat)


def torus(R, r, seg=12, rseg=8, mat='M_Rubber'):
    mb = MB()
    prof = []
    for i in range(rseg + 1):
        a = -math.pi / 2 + math.tau * i / rseg
        prof.append((R + r * math.cos(a), r * math.sin(a)))
    mb.revolve(prof, seg, mat)
    return mb


def sphere(r, mat, seg=7, rings=4, sz=1.0):
    mb = MB()
    prof = [(0, -r * sz)]
    for i in range(1, rings):
        a = -math.pi / 2 + math.pi * i / rings
        prof.append((r * math.cos(a), r * math.sin(a) * sz))
    prof.append((0, r * sz))
    mb.revolve(prof, seg, mat, center=(0, 0, r * sz))
    return mb


def wire(mb, a, b, sag, r=0.007, n=10, mat='M_Rubber', wob=None):
    """Sagging cable a->b made of thin beams."""
    a, b = V(a), V(b)
    pts = []
    for i in range(n + 1):
        t = i / n
        p = a.lerp(b, t) - V(0, 0, sag * 4 * t * (1 - t))
        if wob and 0 < i < n:
            p += V(wob[0] * math.sin(i * 1.7 + wob[2]), wob[1] * math.sin(i * 2.3 + wob[2]), 0)
        pts.append(p)
    for p, q in zip(pts[:-1], pts[1:]):
        mb.beam(p, q, 2 * r, 2 * r, mat)
    return pts


def inner_room(mb, x0, y0, z0, x1, y1, z1, mat='M_WindowDark', floor='M_Concrete'):
    """Dark interior box open towards -Y (faces point inward)."""
    mb.face([V(x0, y1, z0), V(x1, y1, z0), V(x1, y1, z1), V(x0, y1, z1)], mat, normal=(0, -1, 0))
    mb.face([V(x0, y0, z0), V(x0, y1, z0), V(x0, y1, z1), V(x0, y0, z1)], mat, normal=(1, 0, 0))
    mb.face([V(x1, y0, z0), V(x1, y1, z0), V(x1, y1, z1), V(x1, y0, z1)], mat, normal=(-1, 0, 0))
    mb.face([V(x0, y0, z1), V(x1, y0, z1), V(x1, y1, z1), V(x0, y1, z1)], mat, normal=(0, 0, -1))
    mb.face([V(x0, y0, z0), V(x1, y0, z0), V(x1, y1, z0), V(x0, y1, z0)], floor, normal=(0, 0, 1))


def rail(mb, path, h=0.9, mat='M_MetalRust', spacing=0.13, gaps=()):
    """Simple iron railing along a 2D path at z=0 (posts + top & bottom rails). gaps = x-intervals left open."""
    def gapped(x):
        return any(g0 <= x <= g1 for (g0, g1) in gaps)
    for (a, b) in zip(path[:-1], path[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        k = max(1, int(L / spacing))
        for i in range(k + 1):
            t = i / k
            x, y = lerp(a[0], b[0], t), lerp(a[1], b[1], t)
            if gapped(x) and abs(b[1] - a[1]) < 1e-6:
                continue
            mb.box(x - 0.009, y - 0.009, 0.0, x + 0.009, y + 0.009, h, mat)
        segs = [(a, b)]
        if abs(b[1] - a[1]) < 1e-6 and gaps:
            xs = sorted([a[0], b[0]])
            cur = [(xs[0], xs[1])]
            for (g0, g1) in gaps:
                nxt = []
                for (u0, u1) in cur:
                    if g1 <= u0 or g0 >= u1:
                        nxt.append((u0, u1))
                        continue
                    if g0 > u0:
                        nxt.append((u0, g0))
                    if g1 < u1:
                        nxt.append((g1, u1))
                cur = nxt
            segs = [((u0, a[1]), (u1, a[1])) for (u0, u1) in cur if u1 - u0 > 0.05]
        for (p, q) in segs:
            for z, s in ((h, 0.035), (0.08, 0.025), (h * 0.55, 0.02)):
                mb.beam((p[0], p[1], z), (q[0], q[1], z), s, s, mat)
    for (x, y) in path:
        if not gapped(x):
            mb.boxc(x, y, 0, 0.05, 0.05, h + 0.03, mat)


# ------------------------------------------------------------------------------------- garments
def garment(kind, rng, mat):
    """Garment hanging from its top-centre at the origin, in the XZ plane (y ~ 0), double-sided."""
    mb = MB()
    if kind in ('sari', 'towel', 'small', 'dupatta'):
        if kind == 'sari':
            w, L1, L2, nx, nz = rng.uniform(0.9, 1.5), rng.uniform(1.0, 1.6), rng.uniform(0.6, 1.2), 7, 4
        elif kind == 'dupatta':
            w, L1, L2, nx, nz = rng.uniform(0.5, 0.7), rng.uniform(0.9, 1.3), rng.uniform(0.8, 1.2), 4, 4
        elif kind == 'towel':
            w, L1, L2, nx, nz = rng.uniform(0.45, 0.75), rng.uniform(0.45, 0.7), rng.uniform(0.35, 0.6), 4, 2
        else:
            w, L1, L2, nx, nz = rng.uniform(0.25, 0.4), rng.uniform(0.25, 0.4), 0.0, 2, 1
        ph = rng.uniform(0, 6)
        amp = 0.02 + 0.015 * w
        for side, L, y0 in ((-1, L1, -0.008), (1, L2, 0.008)):
            if L <= 0.01:
                continue
            rows = []
            for i in range(nx + 1):
                s = i / nx
                col = []
                for j in range(nz + 1):
                    t = j / nz
                    x = -w / 2 + w * s + (0.03 * math.sin(ph + s * 3) * t)
                    y = y0 + side * 0.01 * t + amp * math.sin(ph + s * math.pi * 3.2) * (0.3 + 0.7 * t)
                    z = -L * t - 0.02 * math.sin(ph * 2 + s * 5) * t
                    col.append(V(x, y, z))
                rows.append(col)
            grid_faces(mb, rows, mat, (0, side, 0), th=0.004)
        return mb
    if kind == 'shirt':
        sw = rng.uniform(0.42, 0.52)
        L = rng.uniform(0.65, 0.8)
        sl = rng.uniform(0.18, 0.28)
        h = sw / 2
        outline = [(-h, 0), (-h - 0.05, -0.02), (-h - sl, -0.18), (-h - sl + 0.08, -0.26), (-h, -0.17), (-h + 0.02, -L),
                   (h - 0.02, -L), (h, -0.17), (h + sl - 0.08, -0.26), (h + sl, -0.18), (h + 0.05, -0.02), (h, 0),
                   (0.07, -0.03), (-0.07, -0.03)]
    elif kind == 'pants':
        hw = rng.uniform(0.18, 0.22)
        L = rng.uniform(0.85, 1.0)
        outline = [(-hw, 0), (hw, 0), (hw + 0.03, -L), (0.04, -L), (0.0, -0.32), (-0.04, -L), (-hw - 0.03, -L)]
    else:   # kurta / frock
        hw = rng.uniform(0.2, 0.26)
        L = rng.uniform(0.8, 1.05)
        outline = [(-hw, 0), (hw, 0), (hw + 0.12, -L), (-hw - 0.12, -L)]
    pts = [V(u, 0.0, v) for (u, v) in outline]
    mb.face_holes(pts, [], (0, -1, 0), mat)
    mb.face_holes([p + V(0, 0.005, 0) for p in pts], [], (0, 1, 0), mat)
    return mb


def laundry_on_line(mb, rng, xa, xb, za, zb, y, sag, n, kinds=None, pegs=True, maxlen=None):
    """Hang n garments on a rope from (xa, y, za) to (xb, y, zb) with sag. Rope is built too."""
    wire(mb, (xa, y, za), (xb, y, zb), sag, r=0.006, n=12, mat='M_Whitewash')
    kinds = kinds or ['shirt', 'shirt', 'sari', 'towel', 'pants', 'small', 'kurta', 'dupatta', 'towel']
    L = xb - xa
    xs = sorted(rng.uniform(0.06, 0.94) for _ in range(n))
    # relax spacing a bit
    xs = [lerp((i + 0.5) / n, x, 0.4) for i, x in enumerate(xs)]
    for t in xs:
        x = xa + L * t
        z = lerp(za, zb, t) - sag * 4 * t * (1 - t)
        slope = ((zb - za) - sag * 4 * (1 - 2 * t)) / L
        g = garment(rng.choice(kinds), rng, rng.choice(LAUNDRY))
        if maxlen:
            b0, b1 = g.bounds()
            if -b0[2] > maxlen:
                g.transform(S(1, 1, maxlen / -b0[2]))
        M = T(x, y, z + 0.005) @ Ry(-math.degrees(math.atan(slope))) @ Rz(rng.uniform(-8, 8))
        mb.add(g, M)
        if pegs:
            mb.boxc(x + rng.uniform(-0.1, 0.1), y, z - 0.04, 0.015, 0.03, z + 0.03, rng.choice(['M_PlasticRed', 'M_PlasticBlue', 'M_PlasticYellow']))


# ------------------------------------------------------------------------------------- small props
def blue_drum(r=0.29, h=0.95, mat='M_PlasticBlue'):
    mb = MB()
    prof = [(0, 0), (r - 0.02, 0), (r, 0.02)]
    for zf in (0.2, 0.5, 0.8):
        z = h * zf
        prof += [(r, z - 0.03), (r + 0.012, z - 0.015), (r + 0.012, z + 0.015), (r, z + 0.03)]
    prof += [(r, h - 0.03), (r - 0.025, h), (0, h)]
    mb.revolve(prof, 20, mat)
    mb.cylinder(r * 0.4, 0.0, h, h + 0.025, 0.04, 10, mat)          # bung
    mb.cylinder(-r * 0.4, 0.0, h, h + 0.02, 0.025, 8, mat)
    return mb


def lpg(mat='M_LPGRed'):
    mb = MB()
    mb.revolve([(0.15, 0.0), (0.155, 0.07), (0.0, 0.07)], 16, mat)                              # foot ring
    mb.revolve([(0, 0.07), (0.16, 0.08), (0.162, 0.48), (0.13, 0.56), (0.06, 0.6), (0, 0.605)], 18, mat)
    mb.revolve([(0.085, 0.58), (0.09, 0.7), (0.08, 0.7), (0.075, 0.6)], 14, mat)              # guard ring
    mb.cylinder(0, 0, 0.6, 0.66, 0.022, 8, 'M_Brass')
    mb.box(-0.03, -0.012, 0.64, 0.04, 0.012, 0.67, 'M_Brass')
    mb.box(-0.05, -0.16, 0.25, 0.05, -0.155, 0.38, 'M_Whitewash')                              # label
    return mb


def matka(s=1.0, mat='M_Terracotta', band=None, seg=14):
    prof = [(0, 0), (0.09, 0.0), (0.17, 0.04), (0.215, 0.11), (0.225, 0.19), (0.2, 0.27), (0.13, 0.33), (0.085, 0.355),
            (0.095, 0.38), (0.1, 0.395), (0.075, 0.395), (0.07, 0.36), (0.0, 0.34)]
    prof = [(r * s, z * s) for (r, z) in prof]
    mb = MB()

    def mf(i, a, b):
        if band and i in (3, 4):
            return band
        return mat
    mb.revolve(prof, seg, mat, matfn=mf)
    return mb


def stool(mat='M_PlasticRed'):
    mb = MB()
    mb.revolve([(0, 0.42), (0.16, 0.42), (0.175, 0.44), (0.17, 0.46), (0, 0.465)], 16, mat)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.beam((sx * 0.105, sy * 0.105, 0.43), (sx * 0.18, sy * 0.18, 0.0), 0.04, 0.028, mat)
    for (a, b) in (((-0.14, -0.14), (0.14, -0.14)), ((0.14, -0.14), (0.14, 0.14)), ((0.14, 0.14), (-0.14, 0.14)),
                   ((-0.14, 0.14), (-0.14, -0.14))):
        mb.beam((a[0] * 1.07, a[1] * 1.07, 0.12), (b[0] * 1.07, b[1] * 1.07, 0.12), 0.02, 0.015, mat)
    return mb


def bucket(mat='M_PlasticRed'):
    mb = MB()
    mb.revolve([(0, 0), (0.12, 0), (0.15, 0.28), (0.16, 0.3), (0.14, 0.3), (0.12, 0.05), (0, 0.05)], 14, mat)
    return mb


def snack_strip(mb, rng, x, y, ztop, n=8, two=True):
    """Hanging strip of snack sachets from (x, y, ztop) downwards."""
    mb.box(x - 0.004, y - 0.004, ztop - n * 0.15 - 0.05, x + 0.004, y + 0.004, ztop, 'M_Whitewash')
    base = rng.choice(SNACKS)
    for i in range(n):
        z1 = ztop - 0.02 - i * 0.15
        cols = (-0.058, 0.058) if two else (0.0,)
        for dx in cols:
            m = base if rng.random() < 0.55 else rng.choice(SNACKS)
            sub = MB()
            sub.box(-0.055, -0.006, -0.16, 0.055, 0.006, 0.0, m)
            sub.box(-0.055, -0.008, -0.025, 0.055, 0.008, 0.0, 'M_SnackFoil')     # crimped top
            mb.add(sub, T(x + dx, y + rng.uniform(-0.01, 0.01), z1) @ Rz(rng.uniform(-14, 14)) @ Ry(rng.uniform(-6, 6)))


# =========================================================================================== shanties
def _paint_skirt(mb, x0, x1, z, mat, cuts, y=0.0):
    for (a, b) in KB.subtract_intervals(x0, x1, cuts):
        mb.box(a, y - 0.012, 0.0, b, y, z, mat)


def _patches(mb, rng, x0, x1, z0, z1, avoid, n, mat='M_BrickExposed', y=0.0):
    """Exposed brick / patch plaster rectangles on a -Y wall at y, avoiding rects (x0,z0,x1,z1)."""
    for _ in range(n):
        for _try in range(20):
            w, h = rng.uniform(0.3, 0.9), rng.uniform(0.25, 0.6)
            px, pz = rng.uniform(x0 + 0.05, x1 - w - 0.05), rng.uniform(z0, max(z0, z1 - h))
            if all(px + w < a - 0.08 or px > c + 0.08 or pz + h < b - 0.08 or pz > d + 0.08 for (a, b, c, d) in avoid):
                mb.box(px, y - 0.009, pz, px + w, y, pz + h, mat)
                avoid.append((px, pz, px + w, pz + h))
                break


def _door(mb_out, rng, op, kind, t, room_y, zroom, mats=None, fy=0.0, xlim=None):
    """Door contents for a door opening op (rect, back_mat None). kind: curtain / open / closed / double.
    Built in the wall frame (wall plane y=0) and shifted by fy."""
    mb = MB()
    cx, sill, w, h = op['cx'], op['sill'], op['w'], op['h']
    a, b = cx - w / 2, cx + w / 2
    if kind == 'curtain':
        mb.rod((a, 0.035, sill + h - 0.06), (b, 0.035, sill + h - 0.06), 0.008, 'M_Steel', seg=5)
        nx, nz = 9, 3
        L = h - rng.uniform(0.15, 0.4)
        ph = rng.uniform(0, 6)
        m = rng.choice(LAUNDRY + ['M_Cloth'])
        rows = []
        for i in range(nx + 1):
            s = i / nx
            col = []
            for j in range(nz + 1):
                tt = j / nz
                col.append(V(a + 0.02 + (w - 0.04) * s, 0.05 + 0.028 * math.sin(ph + s * 9.0), sill + h - 0.06 - L * tt * (1 - 0.1 * s)))
            rows.append(col)
        grid_faces(mb, rows, m, (0, -1, 0), th=0.004)
    elif kind in ('open', 'double'):
        dm = (mats or rng.choice(DOOR_MATS))
        leaves = [(a, 1)] if kind == 'open' else [(a, 1), (b, -1)]
        lw = w if kind == 'open' else w / 2
        for (hx, sg) in leaves:
            ang = rng.uniform(55, 85)
            sub = MB()
            sub.box(0, 0.0, 0, lw - 0.02, 0.035, h - 0.03, dm)
            for zz in (0.25, h * 0.5, h - 0.3):
                sub.box(0.02, -0.01, zz, lw - 0.04, 0.0, zz + 0.06, dm)
            if sg < 0:
                sub.transform(S(-1, 1, 1))
            mb.add(sub, T(hx, t + 0.01, sill) @ Rz(sg * ang))
    else:   # closed: flush metal / wood door with padlock + bands
        dm = (mats or rng.choice(DOOR_MATS))
        mb.box(a, 0.05, sill, b, 0.085, sill + h, dm)
        for zz in (0.3, h * 0.5, h - 0.35):
            mb.box(a + 0.04, 0.035, sill + zz, b - 0.04, 0.05, sill + zz + 0.05, dm)
        mb.box(cx - 0.03, 0.02, sill + 1.0, cx + 0.03, 0.05, sill + 1.1, 'M_Steel')
    if kind != 'closed':
        ra, rb = a - 0.5, b + 0.5
        if xlim:
            ra, rb = max(ra, xlim[0]), min(rb, xlim[1])
        inner_room(mb, ra, t, sill, rb, room_y, zroom)
    mb_out.add(mb, T(0, fy, 0))


def _roof_slope(mb, rng, x0, x1, D, zF, zB, kind, ov=0.35, ovb=0.15, ovs=0.15, weights=True, tarp_p=0.4):
    """Mono-pitch corrugated roof. zF / zB = wall tops at y=0 / y=D. Returns z(y) function and slope sign."""
    rise = zB - zF
    zof = lambda y: zF + 0.05 + rise * y / D
    ang = math.atan2(rise, D)
    if rise >= 0:
        O_y, dirv = -ov, V(0, math.cos(ang), math.sin(ang))
    else:
        O_y, dirv = D + ovb, V(0, -math.cos(ang), -math.sin(ang))
    L = (D + ov + ovb) / math.cos(ang)
    xa, xb = x0 - ovs, x1 + ovs
    x = xa
    i = 0
    while x < xb - 0.05:
        sw = min(rng.uniform(0.85, 1.1), xb - x + 0.04)
        if kind == 'asb':
            mat, pitch, amp = 'M_AsbestosRoof', 0.146, 0.024
        elif kind == 'tin':
            mat, pitch, amp = rng.choice(ROOF_TIN), 0.076, 0.016
        else:
            if rng.random() < 0.5:
                mat, pitch, amp = 'M_AsbestosRoof', 0.146, 0.024
            else:
                mat, pitch, amp = rng.choice(ROOF_TIN), 0.076, 0.016
        lj = rng.uniform(-0.06, 0.04)
        O = V(x, O_y, zof(O_y)) + V(0, 0, 0.012 * (i % 2) + 0.03) + dirv * lj
        corr_sheet(mb, O, (1, 0, 0), dirv, sw, L - lj + rng.uniform(-0.04, 0.03), mat, pitch=pitch, amp=amp, under=mat,
                   N=(0, -dirv.z, dirv.y) if rise >= 0 else (0, dirv.z, -dirv.y), rot=rng.uniform(-0.012, 0.012))
        x += sw - 0.06
        i += 1
    # purlins / rafter stubs under the eave
    for yy in (0.02, D * 0.5, D - 0.05):
        mb.beam((x0 - ovs + 0.05, yy, zof(yy) - 0.035), (x1 + ovs - 0.05, yy, zof(yy) - 0.035), 0.06, 0.05, 'M_WoodPlanks')
    for k in range(3):
        rx = lerp(x0 + 0.2, x1 - 0.2, k / 2) + rng.uniform(-0.1, 0.1)
        y_a, y_b = (0.1, -ov + 0.06) if rise >= 0 else (D - 0.1, D + ovb - 0.04)
        mb.beam((rx, y_a, zof(y_a) - 0.07), (rx, y_b, zof(y_b) - 0.07), 0.05, 0.06, 'M_WoodPlanks')
    deg = math.degrees(ang)
    if weights:
        # bricks along the eave, stones, tyres, a bamboo across
        ye = -ov + 0.15 if rise >= 0 else D + ovb - 0.15
        for _ in range(rng.randint(3, 7)):
            bx = rng.uniform(xa + 0.2, xb - 0.2)
            sub = MB()
            sub.box(-0.115, -0.055, 0, 0.115, 0.055, 0.075, 'M_BrickExposed')
            mb.add(sub, T(bx, ye, zof(ye) + 0.03) @ Rx(deg) @ Rz(rng.uniform(-30, 30)))
        for _ in range(rng.randint(3, 9)):
            yy = rng.uniform(0.1, D - 0.1)
            st = MB()
            stone(st, (0, 0, 0), rng.uniform(0.07, 0.14), rng, rng.choice(['M_Concrete', 'M_Ballast', 'M_BrickExposed']))
            mb.add(st, T(rng.uniform(xa + 0.2, xb - 0.2), yy, zof(yy) + 0.025) @ Rx(deg) @ Rz(rng.uniform(0, 90)))
        for _ in range(rng.choice([0, 0, 1, 2, 3])):
            yy = rng.uniform(0.4, D - 0.4)
            mb.add(torus(rng.uniform(0.22, 0.3), rng.uniform(0.06, 0.08), 12, 6),
                   T(rng.uniform(xa + 0.4, xb - 0.4), yy, zof(yy) + 0.09) @ Rx(deg + rng.uniform(-5, 5)))
        if rng.random() < 0.5:
            yy = rng.uniform(0.3, D - 0.3)
            mb.rod((xa - 0.1, yy, zof(yy) + 0.06), (xb + 0.1, yy + rng.uniform(-0.4, 0.4), zof(yy) + 0.06), 0.035,
                   'M_WoodPlanks', seg=6)
    if rng.random() < tarp_p:
        # blue tarp patch draped over part of the roof
        tw = rng.uniform(1.4, min(3.0, xb - xa - 0.2))
        ta = rng.uniform(xa, xb - tw)
        y0t, y1t = rng.uniform(-ov, D * 0.3), rng.uniform(D * 0.55, D + ovb)
        nx, ny = 7, 6
        rows = []
        ph = rng.uniform(0, 6)
        for i in range(nx + 1):
            col = []
            for j in range(ny + 1):
                s, tt = i / nx, j / ny
                yy = lerp(y0t, y1t, tt)
                bump = 0.05 + 0.04 * math.sin(ph + s * 7 + tt * 5) ** 2
                col.append(V(ta + tw * s, yy, zof(yy) + 0.03 + bump))
            rows.append(col)
        grid_faces(mb, rows, 'M_TarpBlue', (0, -math.sin(ang), math.cos(ang)), th=0.005)
        for _ in range(3):
            yy = rng.uniform(y0t + 0.2, y1t - 0.2)
            st = MB()
            stone(st, (0, 0, 0), 0.1, rng, 'M_Concrete')
            mb.add(st, T(ta + rng.uniform(0.2, tw - 0.2), yy, zof(yy) + 0.1) @ Rx(deg))
    return zof


def _walls(mb, rng, x0, x1, D, z0, zF, zB, front_mat, side_mat, back_mat, ops, t=0.14, front_y=0.0):
    """Front facade with openings (wall plane y=front_y), trapezoid side walls, back wall."""
    sub = MB()
    facade_wall(sub, x0, x1, z0, zF, ops, front_mat)
    mb.add(sub, T(0, front_y, 0))
    y0 = front_y
    for (xa, xb) in ((x0, x0 + t), (x1 - t, x1)):
        bot = [V(xa, y0, z0), V(xb, y0, z0), V(xb, D, z0), V(xa, D, z0)]
        top = [V(xa, y0, zF), V(xb, y0, zF), V(xb, D, zB), V(xa, D, zB)]
        mb.hexa(bot, top, side_mat, skip_bottom=True)
    mb.box(x0 + t, D - t, z0, x1 - t, D, zB, back_mat, skip=('-z',))
    # dark ceiling / interior seen through windows is the back card of the openings


def _meter_and_wires(mb, rng, x0, x1, zF, ov):
    mx = rng.uniform(x0 + 0.25, x0 + 0.6) if rng.random() < 0.5 else rng.uniform(x1 - 0.6, x1 - 0.25)
    mz = min(zF - 0.6, 1.9)
    mb.box(mx - 0.13, -0.11, mz, mx + 0.13, 0.0, mz + 0.32, rng.choice(['M_Steel', 'M_PlasterWhite', 'M_MetalRust']))
    mb.box(mx - 0.1, -0.115, mz + 0.12, mx + 0.1, -0.11, mz + 0.26, 'M_WindowDark')
    # service wires up to the eave and away along the facade
    zt = zF - 0.12
    for k in range(rng.randint(2, 3)):
        dx = (k - 1) * 0.04
        mb.box(mx + dx - 0.005, -0.03, mz + 0.32, mx + dx + 0.005, -0.02, zt, 'M_Rubber')
        tx = x1 + rng.uniform(0.1, 0.4) if mx < 0 else x0 - rng.uniform(0.1, 0.4)
        wire(mb, (mx + dx, -0.03 - 0.02 * k, zt), (tx, -0.05 - 0.04 * k, zt + rng.uniform(-0.1, 0.25)),
             rng.uniform(0.08, 0.3), r=0.006, n=8)
    if rng.random() < 0.6:   # loose drooping cable end
        a = V(mx, -0.04, zt)
        wire(mb, a, a + V(rng.uniform(-0.6, 0.6), -0.05, -rng.uniform(0.3, 0.8)), 0.1, r=0.006, n=5)


def shanty(seed, W, D, p):
    """One storey shanty. p: mat, side, h, slope ('front'|'back'), roof ('asb'|'tin'|'mix'), door, windows."""
    rng = random.Random(seed)
    mb = MB()
    x0, x1 = -W / 2, W / 2
    t = 0.14
    zp = p.get('plinth', rng.uniform(0.18, 0.3))
    H = p.get('h', 2.8)
    rise = rng.uniform(0.35, 0.6)
    zF, zB = (H, H + rise) if p.get('slope', 'front') == 'front' else (H + rise, H)
    wall = p['mat']
    trim = p.get('trim', 'M_PlasterWhite')
    side_mat = p.get('side', 'M_BrickExposed')
    # plinth + ota (raised front platform) + step
    mb.box(x0 - 0.03, 0.0, 0.0, x1 + 0.03, D, zp, 'M_Concrete', skip=('-z',))
    od = p.get('ota', rng.uniform(0.55, 0.95))
    mb.chamfer_box(x0 + rng.uniform(0, 0.15), -od, 0.0, x1 - rng.uniform(0, 0.15), 0.0, zp, 'M_Concrete', ch=0.025)
    # openings
    dw = rng.uniform(0.8, 0.92)
    dh = rng.uniform(1.85, 2.0)
    room = W - 2 * t
    df = p.get('door_x', rng.choice([0.25, 0.3, 0.7, 0.75]))
    dcx = x0 + 0.3 + dw / 2 + (W - 0.6 - dw) * df
    door = dict(kind='rect', cx=dcx, sill=zp + 0.01, w=dw, h=dh, depth=t, fw=0.06, fd=0.03,
                frame_mat=rng.choice([trim, 'M_WoodShutter', 'M_Concrete']), back_mat=None)
    ops = [door]
    avoid = [(dcx - dw / 2 - 0.1, 0, dcx + dw / 2 + 0.1, zp + dh + 0.1)]
    spans = [(x0 + 0.25, dcx - dw / 2 - 0.2), (dcx + dw / 2 + 0.2, x1 - 0.25)]
    nwin = p.get('windows', 2)
    spans.sort(key=lambda s: -(s[1] - s[0]))
    for (a, b) in spans[:nwin]:
        if b - a < 0.75:
            continue
        ww = min(rng.uniform(0.55, 0.8), b - a - 0.15)
        wh = rng.uniform(0.6, 0.85)
        wcx = (a + b) / 2 + rng.uniform(-0.1, 0.1) * (b - a - ww) / 2
        sill = zp + rng.uniform(0.95, 1.1)
        if sill + wh + 0.1 > zF - 0.1:
            wh = zF - 0.2 - sill
        ops.append(dict(kind='rect', cx=wcx, sill=sill, w=ww, h=wh, depth=t, fw=0.05, fd=0.025, frame_mat=trim,
                        fill='bars', ledge=rng.random() < 0.5, hood=rng.random() < 0.3, hood_mat='M_Concrete', hood_depth=0.3,
                        back_mat=rng.choice(['M_WindowDark', 'M_WindowDark', 'M_WoodShutter'])))
        avoid.append((wcx - ww / 2 - 0.1, sill - 0.15, wcx + ww / 2 + 0.1, sill + wh + 0.25))
    ops = KB.keep_fitting(ops, x0, x1, 0.0, zF)
    _walls(mb, rng, x0, x1, D, 0.0, zF, zB, wall, side_mat, side_mat, ops, t)
    # grille on windows (extra horizontal bars) done by 'bars'; door contents + interior
    _door(mb, rng, door, p.get('door', 'curtain'), t, min(D - t - 0.05, 2.2), zp + dh + 0.25, xlim=(x0 + t + 0.01, x1 - t - 0.01))
    # cement skirting + exposed brick / repair patches
    sk = rng.uniform(0.45, 0.8)
    _paint_skirt(mb, x0, x1, sk, p.get('skirt', rng.choice(['M_Concrete', 'M_PlasterWorn', 'M_ConcreteDirty'])),
                 [(dcx - dw / 2 - 0.07, dcx + dw / 2 + 0.07)])
    avoid.append((x0, 0, x1, sk + 0.05))
    _patches(mb, rng, x0 + 0.05, x1 - 0.05, sk + 0.1, zF - 0.3, avoid, rng.randint(1, 3))
    # small sloped tin hood over the door
    if p.get('door_awning', True) and zF - (zp + dh + 0.06) > 0.38:
        za = min(zF - 0.12, zp + dh + 0.42)
        awning_corrugated(mb, dcx - dw / 2 - 0.25, dcx + dw / 2 + 0.25, za, dp=0.55, drop=0.16,
                          mat=rng.choice(['M_CorrugatedRust', 'M_AsbestosRoof', 'M_CorrugatedGalv']))
    ov = rng.uniform(0.3, 0.5)
    _roof_slope(mb, rng, x0, x1, D, zF, zB, p.get('roof', 'mix'), ov=ov, tarp_p=p.get('tarp_p', 0.4))
    _meter_and_wires(mb, rng, x0, x1, zF, ov)
    for k in range(rng.randint(1, 2)):
        wire_hook(mb, rng.uniform(x0 + 0.3, x1 - 0.3), zF - 0.45, 0.0)
    # tarp hanging over one side wall
    if p.get('side_tarp', rng.random() < 0.35):
        sx = x1 + 0.02 if rng.random() < 0.5 else x0 - 0.02
        sgn = 1 if sx > 0 else -1
        ya, yb = rng.uniform(0.2, 1.0), rng.uniform(D * 0.5, D - 0.2)
        rows = []
        for i in range(7):
            s = i / 6
            col = []
            for j in range(5):
                tt = j / 4
                yy = lerp(ya, yb, s)
                ztop = zF + (zB - zF) * yy / D - 0.05
                col.append(V(sx + sgn * (0.02 + 0.04 * math.sin(s * 9 + tt * 3) ** 2), yy, ztop - tt * (ztop - rng.uniform(0.3, 0.9))))
            rows.append(col)
        grid_faces(mb, rows, 'M_TarpBlue', (sgn, 0, 0), th=0.004)
    # clothesline under the front eave
    if p.get('eave_line', rng.random() < 0.5):
        laundry_on_line(mb, rng, x0 + 0.15, x1 - 0.15, zF - 0.15, zF - 0.1, -ov + 0.12, 0.12, max(2, int(W / 1.3)),
                        kinds=['shirt', 'towel', 'small', 'pants', 'kurta'], maxlen=min(1.2, zF - 0.8))
    # clutter on the ota
    cx_free = x1 - 0.45 if dcx < 0 else x0 + 0.45
    if rng.random() < 0.7:
        mb.add(blue_drum(0.25, 0.8), T(cx_free, -0.3, zp) @ Rz(rng.uniform(0, 90)))
    if rng.random() < 0.6:
        mb.add(bucket(rng.choice(['M_PlasticRed', 'M_PlasticBlue', 'M_PlasticYellow'])),
               T(cx_free + (0.5 if cx_free < 0 else -0.5), -0.25, zp))
    if rng.random() < 0.4:
        mb.add(matka(0.9), T(dcx + (0.75 if dcx < cx_free else -0.75), -0.25, zp))
    return mb


SHANTY_1F = [
    ('Shanty_1F_01', 4101, 3.6, 5.0, dict(mat='M_PlasterBlue', h=2.7, roof='asb', door='curtain', windows=1)),
    ('Shanty_1F_02', 4102, 4.2, 6.0, dict(mat='M_PlasterTeal', h=2.9, roof='tin', door='open', windows=2, tarp_p=1.0)),
    ('Shanty_1F_03', 4103, 3.2, 4.5, dict(mat='M_PlasterTurquoise', h=2.6, roof='mix', door='closed', windows=1, side_tarp=True)),
    ('Shanty_1F_04', 4104, 4.8, 6.5, dict(mat='M_PlasterCream', h=3.0, roof='asb', door='curtain', windows=2, slope='back',
                                          trim='M_PlasterBlue')),
    ('Shanty_1F_05', 4105, 3.8, 5.5, dict(mat='M_PlasterPeeling', h=2.8, roof='tin', door='double', windows=1, eave_line=True)),
    ('Shanty_1F_06', 4106, 4.5, 7.0, dict(mat='M_PlasterBlue', h=3.1, roof='mix', door='open', windows=2, side='M_PlasterBlue',
                                          tarp_p=0.0)),
    ('Shanty_1F_07', 4107, 3.4, 5.0, dict(mat='M_PlasterPainted', h=2.7, roof='asb', door='curtain', windows=1, eave_line=True)),
    ('Shanty_1F_08', 4108, 5.0, 6.0, dict(mat='M_PlasterTeal', h=3.2, roof='tin', door='closed', windows=2, slope='back',
                                          eave_line=True, trim='M_PlasterCream')),
]


# ------------------------------------------------------------------------------------- two storey
def dish(r=0.3):
    mb = MB()
    prof = [(0, 0.0)] + [(r * i / 5, 0.09 * (i / 5) ** 2) for i in range(1, 6)]
    mb.revolve(prof, 14, 'M_PlasterWhite')
    mb.revolve(list(reversed([(rr, z - 0.006) for (rr, z) in prof])), 14, 'M_PlasterWhite')
    mb.rod((0, -r * 0.6, 0.09), (0, 0, 0.36), 0.008, 'M_Steel', seg=4)
    mb.cylinder(0, 0, 0.33, 0.41, 0.025, 6, 'M_Steel')
    return mb


def ladder(mb, x, ya, yb, zb, w=0.45, mat='M_MetalRust', extra=0.9):
    """Steel ladder from ground at (x, ya, 0) leaning to (x, yb, zb); rails extend `extra` above zb."""
    d = V(0, yb - ya, zb)
    L = d.length
    u = d / L
    for s in (-1, 1):
        a = V(x + s * w / 2, ya, 0)
        mb.beam(a, a + u * (L + extra), 0.05, 0.02, mat)
    n = int((L + extra * 0.4) / 0.28)
    for i in range(1, n + 1):
        p = V(x, ya, 0) + u * (0.28 * i)
        mb.rod(p + V(-w / 2, 0, 0), p + V(w / 2, 0, 0), 0.012, mat, seg=5)


def shanty_2f(seed, W, D, p):
    rng = random.Random(seed)
    mb = MB()
    x0, x1 = -W / 2, W / 2
    t = 0.14
    zp = rng.uniform(0.18, 0.28)
    H1 = p.get('h1', 2.75)
    H2 = p.get('h2', 2.5)
    wall = p['mat']
    trim = p.get('trim', 'M_PlasterWhite')
    side_mat = p.get('side', 'M_BrickExposed')
    mb.box(x0 - 0.03, 0.0, 0.0, x1 + 0.03, D, zp, 'M_Concrete', skip=('-z',))
    od = rng.uniform(0.6, 0.9)
    mb.chamfer_box(x0 + 0.05, -od, 0.0, x1 - 0.05, 0.0, zp, 'M_Concrete', ch=0.025)
    lad_left = rng.random() < 0.5
    lx = x0 + 0.4 if lad_left else x1 - 0.4
    # ground floor openings: door away from the ladder, window(s), optional shop
    dw, dh = rng.uniform(0.8, 0.95), rng.uniform(1.9, 2.05)
    dcx = (x1 - 0.5 - dw / 2) if lad_left else (x0 + 0.5 + dw / 2)
    ops = []
    shop = p.get('shop', False)
    if shop:
        sw = min(W - 1.6, 2.2)
        scx = (x1 - 0.3 - sw / 2) if lad_left else (x0 + 0.3 + sw / 2)
        sop = dict(kind='rect', cx=scx, sill=zp + 0.01, w=sw, h=2.1, depth=t, fw=0.0, back_mat=None)
        ops.append(sop)
        door = None
    else:
        door = dict(kind='rect', cx=dcx, sill=zp + 0.01, w=dw, h=dh, depth=t, fw=0.06, fd=0.03,
                    frame_mat=rng.choice([trim, 'M_WoodShutter']), back_mat=None)
        ops.append(door)
        a, b = (lx + 0.45, dcx - dw / 2 - 0.2) if lad_left else (dcx + dw / 2 + 0.2, lx - 0.45)
        if b - a > 0.75:
            ww = min(0.75, b - a - 0.15)
            ops.append(dict(kind='rect', cx=(a + b) / 2, sill=zp + 1.0, w=ww, h=0.75, depth=t, fw=0.05, fd=0.025,
                            frame_mat=trim, fill='bars', ledge=True, back_mat='M_WindowDark'))
    ops = KB.keep_fitting(ops, x0, x1, 0.0, H1)
    _walls(mb, rng, x0, x1, D, 0.0, H1, H1, wall, side_mat, side_mat, ops, t)
    if door:
        _door(mb, rng, door, p.get('door', 'curtain'), t, min(D - 0.3, 2.2), zp + dh + 0.2, xlim=(x0 + t + 0.01, x1 - t - 0.01))
        cuts = [(door['cx'] - dw / 2 - 0.07, door['cx'] + dw / 2 + 0.07)]
    else:
        a, b = sop['cx'] - sop['w'] / 2, sop['cx'] + sop['w'] / 2
        inner_room(mb, a - 0.2, t, zp, b + 0.2, min(D - 0.3, 2.4), zp + 2.4)
        mb.box(a + 0.1, 0.5, zp, b - 0.1, 0.85, zp + 0.9, 'M_WoodPlanks')
        rolling_shutter(mb, a, b, zp + 2.1 - rng.uniform(0.3, 0.7), zp + 2.11, y=0.07, housing=True, y_house=0.0)
        signboard(mb, a, b, zp + 2.25, min(H1 - 0.12, zp + 2.75), y=-0.14)
        for k in range(rng.randint(2, 4)):
            snack_strip(mb, rng, a + 0.15 + k * 0.22, -0.2, zp + 2.2, n=rng.randint(4, 7))
        cuts = [(a - 0.02, b + 0.02)]
    _paint_skirt(mb, x0, x1, rng.uniform(0.45, 0.7), rng.choice(['M_Concrete', 'M_ConcreteDirty']), cuts)
    # first floor slab, projecting front balcony/terrace
    bd = p.get('bd', rng.uniform(0.6, 0.9))
    yb = p.get('setback', 0.0)
    zs = H1 + 0.14
    mb.box(x0 - 0.05, -bd, H1, x1 + 0.05, D + 0.02, zs, 'M_Concrete')
    mb.box(x0 - 0.06, -bd - 0.02, H1 - 0.02, x1 + 0.06, -bd + 0.04, zs + 0.06, 'M_ConcreteDirty')
    # upper storey
    upper = p.get('upper', 'brick')
    zu = zs + H2
    rise = rng.uniform(0.3, 0.5)
    ux0, ux1 = x0 + p.get('upper_inset', 0.0), x1
    udw = 0.75
    udx = min(max(lx, ux0 + 0.3 + udw / 2), ux1 - 0.3 - udw / 2)
    if upper == 'tin':
        # corrugated sheet room on a light frame
        for xx in (ux0 + 0.03, ux1 - 0.03):
            for yy in (yb + 0.03, D - 0.03):
                mb.boxc(xx, yy, zs, 0.06, 0.06, zu + (rise if yy > 1 else 0) - 0.02, 'M_WoodPlanks')
        segs = KB.subtract_intervals(ux0, ux1, [(udx - udw / 2, udx + udw / 2)])
        for (a, b) in segs:
            x = a
            while x < b - 0.05:
                sw = min(rng.uniform(0.8, 1.0), b - x)
                corr_sheet(mb, (x, yb - 0.02 - 0.01 * (int(x * 7) % 2), zs + rng.uniform(0.0, 0.05)), (1, 0, 0), (0, 0, 1), sw,
                           H2 - rng.uniform(0.02, 0.1), rng.choice(WALL_TIN), under='M_CorrugatedGalv', rot=rng.uniform(-0.02, 0.02))
                x += sw - 0.04
        corr_sheet(mb, (udx - udw / 2 - 0.05, yb - 0.035, zs + 2.0), (1, 0, 0), (0, 0, 1), udw + 0.1, H2 - 2.0,
                   rng.choice(WALL_TIN), under='M_CorrugatedGalv')
        uop = dict(kind='rect', cx=udx, sill=zs + 0.04, w=udw, h=1.95, depth=0.05, back_mat=None)
        for side_x, nrm in ((ux0, (-1, 0, 0)), (ux1, (1, 0, 0))):
            y = yb
            while y < D - 0.05:
                sw = min(rng.uniform(0.8, 1.0), D - y)
                if nrm[0] > 0:
                    O, U = V(side_x + 0.02, y, zs), V(0, 1, 0)
                else:
                    O, U = V(side_x - 0.02, y + sw, zs), V(0, -1, 0)
                hh = H2 + rise * ((y + sw / 2 - yb) / (D - yb)) - 0.05
                corr_sheet(mb, O, U, (0, 0, 1), sw, hh, rng.choice(WALL_TIN), under='M_CorrugatedGalv')
                y += sw - 0.04
        mb.box(ux0, D - 0.05, zs, ux1, D, zu + rise, 'M_CorrugatedGalv')
        _door(mb, rng, uop, 'curtain' if rng.random() < 0.6 else 'open', 0.02, D - 0.4 - yb, zs + 2.15, fy=yb,
              xlim=(ux0 + 0.05, ux1 - 0.05))
    else:
        umat = {'brick': 'M_BrickExposed', 'plaster': p.get('upper_mat', wall)}[upper]
        uops = [dict(kind='rect', cx=udx, sill=zs + 0.04, w=udw, h=1.95, depth=t, fw=0.0, back_mat=None)]
        a, b = (udx + udw / 2 + 0.25, ux1 - 0.25) if lad_left else (ux0 + 0.25, udx - udw / 2 - 0.25)
        if b - a > 0.8:
            uops.append(dict(kind='rect', cx=(a + b) / 2, sill=zs + 0.95, w=min(0.8, b - a - 0.2), h=0.8, depth=t, fw=0.05,
                             fd=0.025, frame_mat=trim, fill='bars', back_mat='M_WindowDark', ledge=True))
        uops = KB.keep_fitting(uops, ux0, ux1, zs, zu)
        sub = MB()
        _walls(sub, rng, ux0, ux1, D, zs, zu, zu + rise, umat, umat if upper == 'plaster' else 'M_BrickExposed',
               'M_BrickExposed', uops, t, front_y=yb)
        mb.add(sub)
        _door(mb, rng, dict(uops[0], cx=udx), 'curtain' if rng.random() < 0.5 else 'open', t, D - 0.3 - yb, zs + 2.15, fy=yb,
              xlim=(ux0 + t + 0.01, ux1 - t - 0.01))
        if upper == 'plaster':
            _patches(mb, rng, ux0 + 0.1, ux1 - 0.1, zs + 0.2, zu - 0.3,
                     [(udx - 0.6, zs, udx + 0.6, zs + 2.1)] + [(o['cx'] - o['w'] / 2 - 0.1, o['sill'] - 0.1, o['cx'] + o['w'] / 2 + 0.1,
                                                              o['sill'] + o['h'] + 0.2) for o in uops[1:]], 2, y=yb)
    rsub = MB()
    _roof_slope(rsub, rng, ux0, ux1, D - yb, zu, zu + rise, p.get('roof', 'mix'), ov=0.35, tarp_p=p.get('tarp_p', 0.35))
    mb.add(rsub, T(0, yb, 0))
    # railing round the balcony with a gap for the ladder
    rail_sub = MB()
    path = [(x0 - 0.02, yb), (x0 - 0.02, -bd + 0.03), (x1 + 0.02, -bd + 0.03), (x1 + 0.02, yb)]
    rail(rail_sub, path, h=0.9, mat=p.get('rail_mat', 'M_MetalRust'), gaps=[(lx - 0.3, lx + 0.3)])
    mb.add(rail_sub, T(0, 0, zs))
    ladder(mb, lx, -bd - 1.0, -bd + 0.02, zs, mat=p.get('rail_mat', 'M_MetalRust'))
    # laundry: draped over the railing + a line across the balcony
    for k in range(rng.randint(1, 3)):
        cx = rng.uniform(x0 + 0.5, x1 - 0.5)
        if abs(cx - lx) < 0.6:
            continue
        g = garment(rng.choice(['sari', 'towel', 'dupatta']), rng, rng.choice(LAUNDRY))
        g.transform(S(1, 1, 0.6))
        mb.add(g, T(cx, -bd - 0.02, zs + 0.92))
    laundry_on_line(mb, rng, x0 + 0.1, x1 - 0.1, zs + 1.95, zs + 2.0, -bd + 0.35, 0.15, max(3, int(W / 1.0)), maxlen=1.2)
    for xx in (x0 + 0.08, x1 - 0.08):
        mb.box(xx - 0.015, -bd + 0.3, zs, xx + 0.015, -bd + 0.36, zs + 2.05, 'M_MetalRust')
    # roof clutter: black tank on a stand at the back, dish, antenna
    zr = lambda y: zu + 0.05 + rise * (y - yb) / (D - yb)
    if p.get('tank', True):
        ty = D - 0.7
        tx = rng.uniform(x0 + 0.8, x1 - 0.8)
        mb.box(tx - 0.6, ty - 0.6, zr(ty - 0.6) - 0.2, tx + 0.6, ty + 0.6, zr(ty + 0.6) + 0.12, 'M_Concrete')
        mb.add(water_tank('plastic', r=0.5, h=rng.uniform(0.9, 1.1)), T(tx, ty, zr(ty + 0.6) + 0.12))
    if p.get('dish', rng.random() < 0.6):
        sx = ux1 + 0.05 if lad_left else ux0 - 0.05
        mb.box(sx - 0.03, yb - 0.1, zu - 0.6, sx + 0.03, yb + 0.1, zu - 0.45, 'M_Steel')
        mb.add(dish(), T(sx + (0.25 if sx > 0 else -0.25), yb - 0.3, zu - 0.7) @ Rx(-60) @ Rz(rng.uniform(-30, 30)))
    if rng.random() < 0.6:
        ay = rng.uniform(yb + 1.0, D - 1.0)
        mb.add(antenna(rng.uniform(1.6, 2.6)), T(rng.uniform(x0 + 0.4, x1 - 0.4), ay, zr(ay)))
    _meter_and_wires(mb, rng, x0, x1, H1 - 0.1, 0.3)
    if rng.random() < 0.6:
        mb.add(blue_drum(0.25, 0.8), T(lx + (0.65 if lad_left else -0.65), -0.32, zp))
    return mb


SHANTY_2F = [
    ('Shanty_2F_01', 4201, 4.0, 6.0, dict(mat='M_PlasterBlue', upper='brick', roof='asb', door='curtain')),
    ('Shanty_2F_02', 4202, 4.6, 6.5, dict(mat='M_PlasterTeal', upper='tin', roof='tin', door='open', setback=0.6, bd=0.4)),
    ('Shanty_2F_03', 4203, 3.8, 5.5, dict(mat='M_PlasterCream', upper='plaster', upper_mat='M_PlasterPainted', roof='mix',
                                          shop=True, trim='M_PlasterBlue')),
    ('Shanty_2F_04', 4204, 5.0, 7.0, dict(mat='M_PlasterTurquoise', upper='brick', roof='tin', door='double', tarp_p=1.0)),
    ('Shanty_2F_05', 4205, 4.2, 6.0, dict(mat='M_PlasterPainted', upper='plaster', upper_mat='M_PlasterBlue', roof='asb',
                                          door='curtain', setback=0.5, bd=0.5)),
    ('Shanty_2F_06', 4206, 4.4, 6.5, dict(mat='M_PlasterBlue', upper='tin', roof='mix', shop=True, rail_mat='M_Steel')),
]


# ------------------------------------------------------------------------------------- tenements
def tenement(seed, W, D, floors, p):
    rng = random.Random(seed + 77)
    q = dict(p)
    q.setdefault('chhajja_floors', [])
    q.setdefault('cornice_prof', scaled_profile(PROF_BAND_SMALL, 1.4, 1.2))
    q.setdefault('sides', {'front': 'rich', 'left': 'plain', 'right': 'plain', 'back': 'plain'})
    q.setdefault('hooks', 4)
    q.setdefault('ac', 2)
    ro = dict(q.get('roof_opts', {}))
    ro.setdefault('flag', False)
    q['roof_opts'] = ro
    mb = KB.town_house(seed, W, D, floors, q)
    x0, x1 = -W / 2, W / 2
    zf = [0.3, 3.9] + [3.9 + 3.2 * k for k in range(1, floors)]
    bay = q.get('bay', 2.8)
    nb = max(1, int(round(W / bay)))
    bw = W / nb
    centers = [x0 + (i + 0.5) * bw for i in range(nb)]
    balc = set(q.get('balc_floors', [1]))
    # rusty tin hoods over the windows of non-balcony floors
    for f in range(1, floors):
        if f in balc:
            continue
        for cx in centers:
            if rng.random() < 0.75:
                hw = rng.uniform(0.75, 0.95)
                awning_corrugated(mb, cx - hw, cx + hw, zf[f] + 3.0, dp=rng.uniform(0.55, 0.75), drop=0.18,
                                  mat=rng.choice(['M_CorrugatedRust', 'M_CorrugatedRust', 'M_AsbestosRoof', 'M_TarpBlue']))
    # exposed brick piers between bays
    for f in range(1, floors):
        if q.get('floor_mats', {}).get(f) == 'M_BrickExposed':
            continue
        for i in range(nb + 1):
            if rng.random() < 0.45:
                px = x0 + i * bw
                pw = rng.uniform(0.15, 0.22)
                a, b = max(x0 + 0.02, px - pw), min(x1 - 0.02, px + pw)
                z0 = zf[f] + rng.uniform(0.2, 1.2)
                mb.box(a, -0.008, z0, b, 0.0, min(zf[f] + 2.95, z0 + rng.uniform(0.6, 1.6)), 'M_BrickExposed')
    # laundry lines across balcony floors
    for f in sorted(balc):
        if f < floors:
            laundry_on_line(mb, rng, x0 + 0.35, x1 - 0.35, zf[f] + 2.25, zf[f] + 2.3, -0.75, 0.12, max(3, int(W / 1.1)),
                            maxlen=1.3)
    # laundry on poles from the windows of other floors
    for f in range(1, floors):
        if f in balc or rng.random() < 0.4:
            continue
        cx = rng.choice(centers)
        z = zf[f] + 2.55
        for s in (-1, 1):
            mb.rod((cx + s * 0.6, 0.0, z), (cx + s * 0.6, -0.9, z + 0.02), 0.012, 'M_Steel', seg=5)
        laundry_on_line(mb, rng, cx - 0.6, cx + 0.6, z, z, -0.85, 0.03, 2, kinds=['shirt', 'towel', 'small', 'pants'], maxlen=0.8)
    # tangled wires along the facade at the first floor line
    zw = zf[1] + rng.uniform(0.8, 1.4)
    for k in range(rng.randint(3, 5)):
        wire(mb, (x0 - 0.2, -0.25 - 0.05 * k, zw + rng.uniform(-0.2, 0.3)), (x1 + 0.2, -0.3 - 0.04 * k, zw + rng.uniform(-0.2, 0.3)),
             rng.uniform(0.15, 0.5), r=0.007, n=12, mat='M_Rubber')
    # blue tarp hanging down over part of the top floor (rain cover) + dish on the facade corner
    zt_f = zf[floors]
    if q.get('facade_tarp', rng.random() < 0.6):
        side = rng.choice([-1, 1])
        tw = rng.uniform(1.2, 2.0)
        xa = x1 - 0.15 - tw if side > 0 else x0 + 0.15
        drop = rng.uniform(1.4, 2.4)
        rows = []
        ph = rng.uniform(0, 6)
        for i in range(7):
            sx = i / 6
            col = []
            for j in range(5):
                tt = j / 4
                col.append(V(xa + tw * sx + 0.05 * math.sin(ph + tt * 3) * tt, -0.16 - 0.06 * tt - 0.05 * math.sin(ph + sx * 11) ** 2,
                             zt_f - 0.05 - drop * tt * (1 - 0.15 * math.sin(ph + sx * 4) ** 2)))
            rows.append(col)
        grid_faces(mb, rows, 'M_TarpBlue', (0, -1, 0), th=0.004)
        mb.rod((xa - 0.05, -0.16, zt_f - 0.03), (xa + tw + 0.05, -0.16, zt_f - 0.03), 0.015, 'M_WoodPlanks', seg=5)
    if rng.random() < 0.7:
        dx = x0 - 0.05 if rng.random() < 0.5 else x1 + 0.05
        dz = zf[max(1, floors - 1)] + 2.2
        mb.box(dx - 0.03, -0.25, dz, dx + 0.03, 0.0, dz + 0.06, 'M_Steel')
        mb.add(dish(0.3), T(dx, -0.45, dz - 0.25) @ Rx(-60) @ Rz(rng.uniform(-30, 30)))
    # roof: tarp shelter + rebar (rebar via roof_opts)
    ztop = zf[floors] + 0.08 if len(zf) > floors else zf[-1] + 3.2
    if q.get('roof_tarp', True) and not q.get('extra_floor'):
        mb.add(tarp_canopy(rng.uniform(2.4, min(3.4, W - 1.2)), rng.uniform(2.0, 2.4), seed=seed, h=2.1, ropes=False),
               T(rng.uniform(-W * 0.1, W * 0.1), 2.0, ztop))
    return mb


TENEMENTS = [
    ('Tenement_3F_01', 5301, 6.0, 9.0, 3, dict(mat='M_PlasterBlue', trim='M_PlasterWhite', shops=2, balc_floors=[1],
                                              shop_kinds=['shutter_half', 'open'], awning=['corr', 'corr'],
                                              floor_mats={2: 'M_BrickExposed'}, roof_opts=dict(tanks=2, rebar=True, antenna=True))),
    ('Tenement_3F_02', 5302, 5.0, 8.0, 3, dict(mat='M_PlasterTeal', trim='M_PlasterCream', shops=1, balc_floors=[2],
                                              shop_kinds=['shutter'], awning=['corr'], floor_mats={0: 'M_PlasterWorn'},
                                              roof_opts=dict(tanks=1, rebar=True, clothesline=True))),
    ('Tenement_3F_03', 5303, 7.5, 10.0, 3, dict(mat='M_PlasterCream', trim='M_PlasterBlue', shops=3, balc_floors=[1],
                                               shop_kinds=['open', 'shutter_half', 'shutter'], awning=['corr', 'cloth', 'corr'],
                                               roof_opts=dict(tanks=3, rebar=True))),
    ('Tenement_3F_04', 5304, 4.5, 8.0, 3, dict(mat='M_PlasterTurquoise', trim='M_PlasterWhite', shops=1, balc_floors=[],
                                              shop_kinds=['shutter_half'], awning=['corr'],
                                              extra_floor=dict(front=2.0, mat='M_BrickExposed'))),
    ('Tenement_3F_05', 5305, 6.5, 9.0, 3, dict(mat='M_PlasterWorn', trim='M_PlasterTeal', shops=2, balc_floors=[1, 2],
                                              shop_kinds=['shutter', 'open'], awning=['corr', 'corr'],
                                              floor_mats={1: 'M_PlasterTeal'}, roof_opts=dict(tanks=2, rebar=True))),
    ('Tenement_3F_06', 5306, 5.5, 9.0, 3, dict(mat='M_PlasterPeeling', trim='M_PlasterWhite', shops=1, balc_floors=[1],
                                              shop_kinds=['wood'], awning=['corr'], floor_mats={2: 'M_PlasterBlue'},
                                              roof_opts=dict(tanks=2, rebar=True, clothesline=True))),
    ('Tenement_4F_01', 5401, 6.0, 10.0, 4, dict(mat='M_PlasterBlue', trim='M_PlasterWhite', shops=2, balc_floors=[1, 3],
                                               shop_kinds=['shutter_half', 'shutter'], awning=['corr', 'corr'],
                                               floor_mats={3: 'M_BrickExposed'}, roof_opts=dict(tanks=3, rebar=True, antenna=True))),
    ('Tenement_4F_02', 5402, 7.0, 10.0, 4, dict(mat='M_PlasterTeal', trim='M_PlasterWhite', shops=2, balc_floors=[2],
                                               shop_kinds=['open', 'shutter'], awning=['cloth', 'corr'],
                                               floor_mats={0: 'M_PlasterWorn', 1: 'M_PlasterCream'},
                                               roof_opts=dict(tanks=2, rebar=True, clothesline=True))),
    ('Tenement_4F_03', 5403, 5.0, 9.0, 4, dict(mat='M_PlasterCream', trim='M_PlasterTeal', shops=1, balc_floors=[1, 2],
                                              shop_kinds=['shutter'], awning=['corr'],
                                              extra_floor=dict(front=1.5, mat='M_BrickExposed'))),
    ('Tenement_4F_04', 5404, 8.0, 11.0, 4, dict(mat='M_PlasterTurquoise', trim='M_PlasterCream', shops=3, balc_floors=[1],
                                               shop_kinds=['shutter_half', 'open', 'shutter'], awning=['corr', 'corr', 'cloth'],
                                               floor_mats={2: 'M_PlasterBlue', 3: 'M_BrickExposed'},
                                               roof_opts=dict(tanks=3, rebar=True, antenna=True))),
]


# ===================================================================================== corrugated
def _sheet_run(mb, rng, xa, xb, y, zb, H, mats, under='M_CorrugatedGalv', skip=(), patch_p=0.35, hfn=None):
    """Run of vertical-rib sheets along X facing -Y at plane y. skip = x-intervals left open."""
    x = xa
    i = 0
    while x < xb - 0.05:
        sw = min(rng.uniform(0.75, 1.0), xb - x + 0.02)
        a, b = x, x + sw
        if any(not (b <= s0 or a >= s1) for (s0, s1) in skip):
            # clip around the opening
            for (s0, s1) in skip:
                if a < s0 < b:
                    b = s0
                elif a < s1 < b and a >= s0 - 1e-6:
                    a = s1
                elif s0 <= a and b <= s1:
                    a = b
            if b - a < 0.05:
                x += sw - 0.04
                continue
        hh = (hfn((a + b) / 2) if hfn else H) - rng.uniform(0.0, 0.12)
        z0 = zb + rng.uniform(0.0, 0.08)
        m = rng.choice(mats)
        corr_sheet(mb, (a, y - 0.012 * (i % 2), z0), (1, 0, 0), (0, 0, 1), b - a, hh - z0, m, under=under,
                   rot=rng.uniform(-0.02, 0.02))
        if rng.random() < patch_p:
            pw, ph = rng.uniform(0.4, 0.8), rng.uniform(0.4, 0.9)
            pa = rng.uniform(a, max(a, b - pw))
            corr_sheet(mb, (pa, y - 0.03, rng.uniform(z0 + 0.1, hh - ph)), (1, 0, 0), (0, 0, 1), pw, ph, rng.choice(mats + ['M_TinBlue']),
                       rot=rng.uniform(-0.08, 0.08))
        x += sw - 0.04
        i += 1


def corr_shack(seed, W, D, H):
    rng = random.Random(seed)
    mb = MB()
    x0, x1 = -W / 2, W / 2
    rise = rng.uniform(0.3, 0.5)
    zF, zB = H, H + rise
    mats = ['M_CorrugatedRust', 'M_CorrugatedRust', 'M_CorrugatedPainted', 'M_CorrugatedGalv', 'M_MetalRust']
    dw = 0.85
    dcx = rng.uniform(x0 + 0.5 + dw / 2, x1 - 0.5 - dw / 2)
    # posts
    for xx in (x0, x1, (x0 + x1) / 2):
        for yy in (0.05, D - 0.05):
            if yy < 1 and abs(xx - dcx) < dw / 2 + 0.12:
                continue
            mb.boxc(xx, yy, 0, 0.07, 0.07, zF + (zB - zF) * yy / D, 'M_WoodPlanks')
    mb.box(x0, 0.0, 0.0, x1, D, 0.06, 'M_Concrete', skip=('-z',))
    _sheet_run(mb, rng, x0, x1, 0.0, 0.0, zF, mats, skip=[(dcx - dw / 2, dcx + dw / 2)])
    # over-door sheet
    corr_sheet(mb, (dcx - dw / 2 - 0.05, -0.025, 1.95), (1, 0, 0), (0, 0, 1), dw + 0.1, zF - 1.95, rng.choice(mats), under='M_CorrugatedGalv')
    # tin door, ajar outward, with a wooden frame
    sub = MB()
    corr_sheet(sub, (0, 0, 0), (1, 0, 0), (0, 0, 1), dw - 0.04, 1.9, rng.choice(['M_TinBlue', 'M_CorrugatedPainted', 'M_CorrugatedRust']),
               under='M_CorrugatedGalv')
    for zz in (0.05, 0.9, 1.8):
        sub.box(0, 0.0, zz, dw - 0.04, 0.04, zz + 0.07, 'M_WoodPlanks')
    sub.box(dw * 0.5, -0.03, 0.95, dw * 0.5 + 0.06, -0.01, 1.0, 'M_Steel')
    mb.add(sub, T(dcx - dw / 2 + 0.02, -0.02, 0.04) @ Rz(-rng.uniform(10, 35)))
    for xx in (dcx - dw / 2, dcx + dw / 2):
        mb.box(xx - 0.035, -0.05, 0, xx + 0.035, 0.02, 1.97, 'M_WoodPlanks')
    inner_room(mb, x0 + 0.05, 0.02, 0.06, x1 - 0.05, D - 0.06, zF - 0.02)
    # sides + back
    hl = lambda y: zF + (zB - zF) * y / D
    # side walls: Rz(90) maps local +x -> world +y and local -y -> world +x (and Rz(-90) the mirror)
    sub = MB()
    _sheet_run(sub, rng, 0.0, D, 0.0, 0.0, 0, mats, hfn=hl, patch_p=0.2)
    mb.add(sub, T(x1, 0, 0) @ Rz(90))
    sub = MB()
    _sheet_run(sub, rng, -D, 0.0, 0.0, 0.0, 0, mats, hfn=lambda u: hl(-u), patch_p=0.2)
    mb.add(sub, T(x0, 0, 0) @ Rz(-90))
    sub = MB()
    _sheet_run(sub, rng, x0, x1, 0.0, 0.0, zB, mats, patch_p=0.2)
    mb.add(sub, T(0, D, 0) @ Rz(180))
    # bricks/stones holding the base
    for _ in range(rng.randint(6, 12)):
        st = MB()
        stone(st, (0, 0, 0), rng.uniform(0.06, 0.1), rng, rng.choice(['M_BrickExposed', 'M_Concrete']))
        xx = rng.uniform(x0 + 0.1, x1 - 0.1)
        if abs(xx - dcx) < dw / 2 + 0.1:
            continue
        mb.add(st, T(xx, -0.1, 0))
    _roof_slope(mb, rng, x0, x1, D, zF, zB, 'tin', ov=0.3, ovb=0.1, ovs=0.1, tarp_p=0.4)
    if rng.random() < 0.5:
        mb.add(blue_drum(0.25, 0.8), T(x1 - 0.4 if dcx < 0 else x0 + 0.4, -0.45, 0))
    return mb


def corr_wall(seed=4600, L=6.0):
    rng = random.Random(seed)
    mb = MB()
    x0, x1 = -L / 2, L / 2
    mats = ['M_CorrugatedRust', 'M_CorrugatedRust', 'M_CorrugatedPainted', 'M_CorrugatedGalv', 'M_TinBlue', 'M_MetalRust']
    # posts + rails behind
    n = int(L / 2) + 1
    for i in range(n):
        x = lerp(x0 + 0.1, x1 - 0.1, i / (n - 1))
        lean = rng.uniform(-0.05, 0.05)
        mb.beam((x, 0.065, 0), (x + lean, 0.065, 2.55), 0.07, 0.07, rng.choice(['M_WoodPlanks', 'M_MetalRust']))
    for z in (0.35, 1.3, 2.25):
        for yy in (0.035, 0.095):
            mb.beam((x0, yy, z), (x1, yy, z + rng.uniform(-0.05, 0.05)), 0.03, 0.06, 'M_WoodPlanks')
    _sheet_run(mb, rng, x0, x1, 0.0, 0.0, 0, mats, under=None, patch_p=0.45,
               hfn=lambda x: 2.45 + 0.12 * math.sin(x * 1.7 + 1.0))
    # back side of the sheets (galvanised) for the alley behind
    sub = MB()
    _sheet_run(sub, random.Random(seed + 1), x0, x1, 0.0, 0.0, 0, ['M_CorrugatedGalv', 'M_CorrugatedRust'], under=None, patch_p=0.1,
               hfn=lambda x: 2.4 + 0.12 * math.sin(-x * 1.7 + 1.0))
    mb.add(sub, T(0, 0.13, 0) @ Rz(180))
    for _ in range(14):
        st = MB()
        stone(st, (0, 0, 0), rng.uniform(0.06, 0.12), rng, rng.choice(['M_BrickExposed', 'M_Concrete', 'M_Ballast']))
        mb.add(st, T(rng.uniform(x0, x1), rng.uniform(-0.2, -0.08), 0))
    # a poster / painted ad on one sheet
    px = rng.uniform(x0 + 0.5, x1 - 1.3)
    o = V(px, -0.045, 1.0)
    mb.face([o, o + V(0.8, 0, 0), o + V(0.8, 0, 0.6), o + V(0, 0, 0.6)], 'M_Poster', normal=(0, -1, 0),
            uvo=(o, Vector((1, 0, 0)), Vector((0, 0, 1)), 0.8, 0.6))
    return mb


# ===================================================================================== gateway
def gateway(seed=4700):
    rng = random.Random(seed)
    mb = MB()
    gap = 3.2
    c = 0.45
    zl, zt = 2.9, 3.5
    for s in (-1, 1):
        cx = s * (gap / 2 + c / 2)
        mb.chamfer_box(cx - c / 2, -c / 2, 0, cx + c / 2, c / 2, zl, 'M_Concrete', ch=0.015)
        mb.box(cx - c / 2 - 0.05, -c / 2 - 0.05, 0, cx + c / 2 + 0.05, c / 2 + 0.05, 0.35, 'M_ConcreteDirty')   # plinth
        # painted band
        mb.box(cx - c / 2 - 0.004, -c / 2 - 0.004, 0.35, cx + c / 2 + 0.004, c / 2 + 0.004, 0.75,
               'M_PlasterBlue' if s < 0 else 'M_PlasterTeal')
        # posters on the column faces (both sides of the passage)
        for face_y, nrm in ((-c / 2 - 0.006, -1), (c / 2 + 0.006, 1)):
            for k in range(rng.randint(1, 3)):
                pw, ph = rng.uniform(0.25, 0.38), rng.uniform(0.35, 0.55)
                pz = rng.uniform(0.9, 2.2)
                px = cx + rng.uniform(-c / 2 + 0.02, c / 2 - pw - 0.02)
                fy = face_y + nrm * 0.002 * k
                o = V(px, fy, pz)
                u = Vector((1, 0, 0)) if nrm < 0 else Vector((-1, 0, 0))
                if nrm > 0:
                    o = V(px + pw, fy, pz)
                pts = [o, o + u * pw, o + u * pw + V(0, 0, ph), o + V(0, 0, ph)]
                mb.face(pts, 'M_Poster', normal=(0, nrm, 0), uvo=(o, u, Vector((0, 0, 1)), pw, ph))
    # deep lintel slab with a lip and a painted name board
    L = gap + 2 * c + 0.3
    mb.chamfer_box(-L / 2, -0.35, zl, L / 2, 0.35, zt, 'M_Concrete', ch=0.02, skip_bottom=False)
    mb.box(-L / 2 - 0.04, -0.39, zt - 0.06, L / 2 + 0.04, 0.39, zt + 0.02, 'M_ConcreteDirty')
    o = V(-1.3, -0.356, zl + 0.1)
    mb.face([o, o + V(2.6, 0, 0), o + V(2.6, 0, 0.4), o + V(0, 0, 0.4)], 'M_Signboard', normal=(0, -1, 0),
            uvo=(o, Vector((1, 0, 0)), Vector((0, 0, 1)), 2.6, 0.4))
    # rain stains streaking down from the lintel (thin dark plaster sheets)
    for _ in range(6):
        sx = rng.uniform(-L / 2 + 0.1, L / 2 - 0.4)
        if abs(sx) < gap / 2 - 0.1 and rng.random() < 0.7:
            continue
        mb.box(sx, -0.358, zl + rng.uniform(0.0, 0.1), sx + rng.uniform(0.1, 0.3), -0.352, zt - 0.08, 'M_ConcreteDirty')
    # rebar stubs + wires over the top
    for x in (-L / 2 + 0.2, L / 2 - 0.2):
        rebar_stubs(mb, x, 0.0, zt + 0.02, 4, rng.uniform(0.3, 0.6))
    for k in range(4):
        wire(mb, (-L / 2 - 0.3, rng.uniform(-0.3, 0.3), zt + rng.uniform(0.1, 0.5)),
             (L / 2 + 0.3, rng.uniform(-0.3, 0.3), zt + rng.uniform(0.1, 0.5)), rng.uniform(0.05, 0.25), r=0.008, n=10)
    wire_hook(mb, -1.0, zl + 0.2, -0.35)
    # tube light under the lintel
    mb.box(-0.6, -0.04, zl - 0.06, 0.6, 0.04, zl - 0.02, 'M_Whitewash')
    return mb


# ===================================================================================== props
def laundry_line(L, seed):
    rng = random.Random(seed)
    mb = MB()
    z = 3.2
    sag = 0.25 if L < 8 else 0.42
    for s in (-1, 1):
        x = s * L / 2
        mb.box(x - 0.02, -0.02, z - 0.06, x + 0.02, 0.02, z + 0.06, 'M_MetalRust')     # hook plate
        mb.rod((x, 0, z), (x - s * 0.08, 0, z), 0.008, 'M_Steel', seg=5)
    n = 8 if L < 8 else 14
    laundry_on_line(mb, rng, -L / 2 + 0.08, L / 2 - 0.08, z, z, 0.0, sag, n, maxlen=1.6)
    return mb


def chai_stall(seed=4800):
    rng = random.Random(seed)
    mb = MB()
    # counter
    mb.box(-0.9, 0.0, 0.0, 0.9, 0.6, 0.95, 'M_WoodPlanks')
    mb.box(-0.95, -0.04, 0.95, 0.95, 0.65, 0.98, 'M_TeaSteel')
    o = V(-0.85, -0.006, 0.15)
    mb.face([o, o + V(1.7, 0, 0), o + V(1.7, 0, 0.72), o + V(0, 0, 0.72)], 'M_Signboard', normal=(0, -1, 0),
            uvo=(o, Vector((1, 0, 0)), Vector((0, 0, 1)), 1.7, 0.72))
    mb.box(-0.9, -0.02, 0.0, 0.9, 0.0, 0.12, 'M_TinBlue')
    # raised shelf with glass jars
    mb.box(-0.88, 0.0, 0.98, 0.15, 0.28, 1.1, 'M_WoodPlanks')
    for i in range(6):
        jx = -0.8 + i * 0.16
        mb.cylinder(jx, 0.13, 1.1, 1.33, 0.065, 10, 'M_Glass')
        mb.cylinder(jx, 0.13, 1.33, 1.37, 0.05, 10, rng.choice(['M_PlasticRed', 'M_PlasticYellow', 'M_PlasticBlue']))
        mb.cylinder(jx, 0.13, 1.12, 1.12 + rng.uniform(0.08, 0.16), 0.058, 8, rng.choice(SNACKS[:4] + ['M_VegBrown']))
    # gas stove + big pot
    mb.box(0.3, 0.2, 0.98, 0.85, 0.55, 1.06, 'M_Steel')
    mb.cylinder(0.55, 0.37, 1.06, 1.08, 0.1, 10, 'M_Rubber')
    mb.revolve([(0, 1.08), (0.17, 1.08), (0.18, 1.1), (0.18, 1.34), (0.19, 1.35), (0.17, 1.35), (0.17, 1.12), (0, 1.12)], 16,
               'M_TeaSteel', center=(0.55, 0.37, 0))
    for s in (-1, 1):
        mb.beam((0.55 + s * 0.18, 0.37, 1.3), (0.55 + s * 0.24, 0.37, 1.3), 0.02, 0.02, 'M_TeaSteel')
    # brass kettle
    kx, ky = 0.2, 0.42
    mb.revolve([(0, 0.98), (0.09, 0.98), (0.11, 1.05), (0.09, 1.14), (0.05, 1.18), (0.04, 1.21), (0, 1.21)], 12, 'M_Brass',
               center=(kx, ky, 0))
    mb.rod((kx - 0.08, ky, 1.04), (kx - 0.19, ky, 1.15), 0.012, 'M_Brass', seg=6)
    mb.beam((kx + 0.06, ky, 1.17), (kx + 0.12, ky, 1.08), 0.02, 0.015, 'M_Brass')
    mb.beam((kx + 0.03, ky, 1.19), (kx + 0.07, ky, 1.17), 0.02, 0.015, 'M_Brass')
    # steel tray with cutting-chai glasses
    mb.box(0.25, -0.02, 0.98, 0.7, 0.16, 0.99, 'M_TeaSteel')
    for i in range(8):
        gx, gy = 0.3 + (i % 4) * 0.11, 0.03 + (i // 4) * 0.09
        mb.cylinder(gx, gy, 0.99, 1.08, 0.025, 8, 'M_TeaSteel', r_top=0.032)
    # LPG under/behind the counter, vendor stool
    mb.add(lpg(), T(0.55, 0.95, 0))
    mb.add(stool('M_PlasticBlue'), T(-0.4, 1.05, 0))
    mb.add(bucket('M_PlasticRed'), T(-0.2, 0.85, 0) @ S(0.8))
    # bamboo / steel frame
    posts = [(-1.0, -0.35, 2.2), (1.0, -0.35, 2.2), (-1.0, 1.35, 2.5), (1.0, 1.35, 2.5)]
    for (px, py, h) in posts:
        mb.cylinder(px, py, 0.0, h, 0.035, 7, 'M_WoodPlanks')
    mb.rod((-1.05, -0.35, 2.15), (1.05, -0.35, 2.15), 0.03, 'M_WoodPlanks', seg=6)
    mb.rod((-1.05, 1.35, 2.45), (1.05, 1.35, 2.45), 0.03, 'M_WoodPlanks', seg=6)
    for s in (-1, 1):
        mb.rod((s * 1.0, -0.4, 2.17), (s * 1.0, 1.4, 2.47), 0.028, 'M_WoodPlanks', seg=6)
    # sagging blue tarp roof
    nx, ny = 8, 6
    rows = []
    for i in range(nx + 1):
        col = []
        for j in range(ny + 1):
            s, t = i / nx, j / ny
            y = lerp(-0.6, 1.5, t)
            z = lerp(2.17, 2.52, (y + 0.35) / 1.7) + 0.03 - 0.1 * math.sin(math.pi * s) * math.sin(math.pi * min(1, max(0, (y + 0.35) / 1.7)))
            if y < -0.35:
                z = 2.18 - (-0.35 - y) * 0.6
            col.append(V(lerp(-1.18, 1.18, s), y, z + 0.02 * math.sin(s * 11 + t * 7)))
        rows.append(col)
    grid_faces(mb, rows, 'M_TarpBlue', (0, -0.2, 1), th=0.005)
    # snack strips hanging from the front beam + a name board above
    for k in range(7):
        snack_strip(mb, rng, -0.9 + k * 0.3 + rng.uniform(-0.04, 0.04), -0.38, 2.12, n=rng.randint(5, 7))
    o = V(-0.8, -0.42, 2.25)
    mb.box(-0.82, -0.42, 2.23, 0.82, -0.38, 2.62, 'M_MetalRust')
    mb.face([o, o + V(1.6, 0, 0), o + V(1.6, 0, 0.35), o + V(0, 0, 0.35)], 'M_Signboard', normal=(0, -1, 0),
            uvo=(o, Vector((1, 0, 0)), Vector((0, 0, 1)), 1.6, 0.35))
    # milk crate + biscuit boxes on the ground
    mb.box(0.95, -0.3, 0.0, 1.35, 0.1, 0.3, 'M_PlasticYellow')
    return mb


def snack_strip_asset(seed=4810):
    rng = random.Random(seed)
    mb = MB()
    mb.rod((-0.08, 0, 0.0), (0.08, 0, 0.0), 0.006, 'M_Steel', seg=5)
    snack_strip(mb, rng, 0.0, 0.0, 0.0, n=8)
    return mb


def veg_cart(seed=4820):
    rng = random.Random(seed)
    mb = MB()
    L, Wd, zt = 1.7, 0.9, 0.72
    mb.box(-L / 2, -Wd / 2, zt - 0.05, L / 2, Wd / 2, zt, 'M_WoodPlanks')
    for s in (-1, 1):
        mb.box(-L / 2, s * Wd / 2 - 0.02, zt, L / 2, s * Wd / 2 + 0.02, zt + 0.09, 'M_WoodPlanks')
        mb.box(s * L / 2 - 0.02, -Wd / 2, zt, s * L / 2 + 0.02, Wd / 2, zt + 0.09, 'M_WoodPlanks')
        mb.beam((-L / 2 - 0.55, s * 0.35, zt + 0.12), (L / 2, s * 0.35, zt - 0.08), 0.05, 0.05, 'M_WoodPlanks')   # chassis/handles
        # bicycle wheel
        wy = s * (Wd / 2 + 0.06)
        wh = MB()
        wh.add(torus(0.33, 0.022, 20, 6, 'M_Rubber'))
        wh.add(torus(0.305, 0.01, 20, 4, 'M_Steel'))
        for k in range(10):
            a = math.tau * k / 10
            wh.rod((0, 0, 0), (0.3 * math.cos(a), 0.3 * math.sin(a), 0), 0.003, 'M_Steel', seg=3)
        mb.add(wh, T(0.1, wy, 0.355) @ Rx(90))
    mb.rod((0.1, -Wd / 2 - 0.08, 0.355), (0.1, Wd / 2 + 0.08, 0.355), 0.02, 'M_Steel', seg=6)
    for s in (-1, 1):
        mb.beam((0.1, s * 0.35, 0.36), (0.1, s * 0.35, zt - 0.05), 0.04, 0.04, 'M_Steel')
        mb.beam((L / 2 - 0.1, s * 0.35, 0.0), (L / 2 - 0.1, s * 0.35, zt - 0.05), 0.05, 0.05, 'M_WoodPlanks')
        mb.cylinder(-L / 2 - 0.55, s * 0.35, zt + 0.06, zt + 0.18, 0.025, 6, 'M_Rubber')
    # sacking on the platform
    mb.box(-L / 2 + 0.03, -Wd / 2 + 0.03, zt, L / 2 - 0.03, Wd / 2 - 0.03, zt + 0.01, 'M_SackGreen')

    def heap(cx, cy, rx, ry, h, item, mat, n, r):
        mb.revolve([(0, 0), (rx * 0.95, 0.0), (rx * 0.7, h * 0.55), (0, h * 0.85)], 10, mat, center=(cx, cy, zt + 0.01),
                   sx=1.0, sy=ry / rx)
        for _ in range(n):
            a = rng.uniform(0, math.tau)
            d = math.sqrt(rng.random())
            px, py = cx + math.cos(a) * rx * d * 0.9, cy + math.sin(a) * ry * d * 0.9
            pz = zt + h * 0.85 * (1 - d * d) * 0.95
            if item == 'sphere':
                mb.add(sphere(r * rng.uniform(0.85, 1.15), mat, 6, 3, sz=rng.uniform(0.8, 1.0)), T(px, py, pz - r * 0.4))
            else:
                b = rng.uniform(0, 180)
                l = r * rng.uniform(0.8, 1.2)
                mb.beam((px, py, pz), (px + l * math.cos(math.radians(b)), py + l * math.sin(math.radians(b)), pz + 0.01),
                        0.012, 0.012, mat)
    heap(-0.5, 0.0, 0.3, 0.35, 0.26, 'sphere', 'M_VegRed', 45, 0.035)
    heap(0.05, -0.18, 0.25, 0.2, 0.2, 'sphere', 'M_Onion', 22, 0.035)
    heap(0.05, 0.2, 0.25, 0.18, 0.16, 'stick', 'M_VegGreen', 40, 0.09)
    heap(0.55, 0.0, 0.25, 0.33, 0.2, 'sphere', 'M_VegBrown', 25, 0.035)
    # leafy bundles
    for k in range(3):
        mb.add(sphere(0.07, 'M_VegGreen', 6, 3, sz=0.6), T(0.7 + rng.uniform(-0.05, 0.05), -0.32 + k * 0.1, zt))
    # balance scale on a post at the front corner
    sx, sy = -0.75, -0.38
    mb.cylinder(sx, sy, zt, zt + 0.6, 0.012, 6, 'M_Steel')
    mb.beam((sx - 0.22, sy, zt + 0.58), (sx + 0.22, sy, zt + 0.58), 0.015, 0.012, 'M_Steel')
    for s in (-1, 1):
        px = sx + s * 0.2
        for d in ((0.06, 0), (-0.03, 0.05), (-0.03, -0.05)):
            mb.beam((px, sy, zt + 0.58), (px + d[0], sy + d[1], zt + 0.3), 0.004, 0.004, 'M_Steel')
        mb.revolve([(0, zt + 0.27), (0.09, zt + 0.3), (0.085, zt + 0.31), (0, zt + 0.29)], 12, 'M_Brass', center=(px, sy, 0))
    return mb


def matka_stack(seed=4830):
    rng = random.Random(seed)
    mb = MB()
    mb.box(-0.9, -0.5, 0.0, 0.9, 0.5, 0.04, 'M_WoodPlanks')
    spots = [(-0.6, -0.2), (-0.1, -0.25), (0.4, -0.2), (-0.4, 0.25), (0.15, 0.25), (0.65, 0.25)]
    for i, (x, y) in enumerate(spots):
        s = rng.uniform(1.0, 1.3)
        mat = 'M_ClayGreen' if i == 4 else 'M_Terracotta'
        band = rng.choice([None, 'M_Whitewash', 'M_Saffron', None])
        mb.add(matka(s, mat, band), T(x, y, 0.04) @ Rz(rng.uniform(0, 90)))
        hz = 0.04 + 0.395 * s
        # stacked inverted pots on some
        if i in (0, 5):
            k = 1 if i == 5 else 2
            z = 0.04 + 0.32 * s
            for j in range(k):
                s2 = s * rng.uniform(0.85, 0.95)
                mb.add(matka(s2, 'M_Terracotta', None), T(x + rng.uniform(-0.02, 0.02), y, z + 0.395 * s2) @ Rx(180))
                z += 0.28 * s2
    # small kulhads / diyas in front
    for k in range(7):
        x = rng.uniform(-0.8, 0.8)
        mb.revolve([(0, 0), (0.03, 0), (0.045, 0.08), (0.04, 0.08), (0.025, 0.012), (0, 0.012)], 8, 'M_Terracotta',
                   center=(x, -0.42, 0.04))
    return mb


def sack(l, w, h, mat, ear=True):
    mb = MB()
    prof = [(0, -h / 2), (0.75, -h * 0.48), (0.95, -h * 0.32), (1.0, 0.0), (0.95, h * 0.3), (0.75, h * 0.46), (0, h / 2)]
    prof = [(r, z + h / 2) for (r, z) in prof]
    # squarish pillow in plan (superellipse lobe)
    sq = lambda th: 1.0 / ((abs(math.cos(th)) ** 5 + abs(math.sin(th)) ** 5) ** 0.2)
    mb.revolve(prof, 16, mat, sx=l / 2 * 0.93, sy=w / 2 * 0.93, lobe=sq, phase=math.pi / 16)
    if ear:
        for s in (-1, 1):
            mb.hexa([(s * l / 2 * 0.95, -0.05, h * 0.4), (s * l / 2 * 0.95, 0.05, h * 0.4), (s * l / 2 * 0.95, 0.05, h * 0.6),
                     (s * l / 2 * 0.95, -0.05, h * 0.6)],
                    [(s * (l / 2 + 0.07), -0.03, h * 0.45), (s * (l / 2 + 0.07), 0.03, h * 0.45), (s * (l / 2 + 0.07), 0.03, h * 0.55),
                     (s * (l / 2 + 0.07), -0.03, h * 0.55)], mat)
    return mb


def bale(l, w, h, mat, rng):
    mb = MB()
    mb.chamfer_box(-l / 2, -w / 2, 0, l / 2, w / 2, h, mat, ch=0.05, skip_bottom=False)
    for k in range(2):
        x = lerp(-l / 2 + 0.2, l / 2 - 0.2, k)
        mb.box(x - 0.015, -w / 2 - 0.01, -0.005, x + 0.015, w / 2 + 0.01, h + 0.01, 'M_Rubber', skip=('-z',))
    # bulges / stray plastic
    for _ in range(3):
        st = MB()
        stone(st, (0, 0, 0), rng.uniform(0.05, 0.1), rng, rng.choice(['M_SackBlue', 'M_SackWhite', 'M_PlasticRed']))
        mb.add(st, T(rng.uniform(-l / 2 + 0.1, l / 2 - 0.1), -w / 2 + 0.02, rng.uniform(0.1, h - 0.2)) @ Rx(90))
    return mb


SACK_MATS = ['M_SackWhite', 'M_SackWhite', 'M_SackGreen', 'M_SackBlue', 'M_SackBeige']


def sack_pile(kind, seed):
    rng = random.Random(seed)
    mb = MB()
    if kind == 1:
        # loose heap of sacks ~1.3 m high
        layers = [(7, 2.4, 1.5), (5, 1.9, 1.1), (3, 1.3, 0.7), (1, 0.6, 0.3)]
        z = 0.0
        for (n, lx, ly) in layers:
            for i in range(n):
                l, w, h = rng.uniform(0.75, 0.95), rng.uniform(0.45, 0.55), rng.uniform(0.28, 0.36)
                mb.add(sack(l, w, h, rng.choice(SACK_MATS)), T(rng.uniform(-lx / 2 + 0.4, lx / 2 - 0.4), rng.uniform(-ly / 2 + 0.2, ly / 2 - 0.2),
                                                             z - 0.03) @ Rz(rng.uniform(-35, 35) + rng.choice([0, 90])) @ Rx(rng.uniform(-8, 8)))
            z += 0.27
    elif kind == 2:
        # stacked compressed plastic bales ~2.4 m
        for layer in range(3):
            for i in range(3 - (layer == 2)):
                for j in range(2):
                    l, w, h = rng.uniform(0.95, 1.05), rng.uniform(0.75, 0.85), rng.uniform(0.7, 0.8)
                    x = (i - 1 + 0.5 * (layer == 2)) * 1.05 + rng.uniform(-0.06, 0.06)
                    y = (j - 0.5) * 0.85 + rng.uniform(-0.05, 0.05)
                    mb.add(bale(l, w, h, rng.choice(['M_SackWhite', 'M_SackBlue', 'M_SackBeige', 'M_SackGreen']), rng),
                           T(x, y, layer * 0.79) @ Rz(rng.uniform(-4, 4)))
    else:
        # jumbo bags + sacks leaning against them
        for (x, y, mat) in ((-0.6, 0.2, 'M_SackWhite'), (0.55, 0.25, 'M_SackWhite'), (0.0, 0.3, 'M_SackBeige')):
            s = rng.uniform(0.9, 1.05)
            if mat == 'M_SackBeige':
                mb.add(sack(1.1, 0.9, 1.0, 'M_SackBlue', ear=False), T(x, y + 0.2, 1.2) @ Rz(rng.uniform(0, 30)))
                mb.add(bale(1.0, 0.9, 1.2, 'M_SackWhite', rng), T(x, y + 0.3, 0))
                continue
            mb.revolve([(0, 0), (0.5 * s, 0), (0.55 * s, 0.1), (0.56 * s, 0.9 * s), (0.45 * s, 1.0 * s), (0.2 * s, 1.05 * s), (0, 1.08 * s)],
                       4, mat, center=(x, y, 0), phase=math.pi / 4, lobe=lambda th: 1.0 + 0.06 * math.sin(th * 4))
            for k in range(4):
                a = math.pi / 4 + k * math.pi / 2
                px, py = x + 0.36 * s * math.cos(a), y + 0.36 * s * math.sin(a)
                mb.beam((px, py, 1.0 * s), (px, py, 1.2 * s), 0.05, 0.015, 'M_SackBlue')
        for i in range(6):
            mb.add(sack(rng.uniform(0.75, 0.9), 0.5, 0.32, rng.choice(SACK_MATS)),
                   T(rng.uniform(-1.1, 1.1), rng.uniform(-0.75, -0.4), rng.choice([0, 0, 0.25])) @ Rz(rng.uniform(-30, 30)))
    return mb


def cricket_stumps():
    mb = MB()
    mb.box(-0.2, -0.12, 0, 0.2, 0.12, 0.06, 'M_PlasticYellow')
    for x in (-0.1, 0.0, 0.1):
        mb.cylinder(x, 0, 0.06, 0.71, 0.018, 8, 'M_BatWillow')
        mb.cylinder(x, 0, 0.71, 0.72, 0.012, 8, 'M_BatWillow')
    for x0, x1 in ((-0.105, -0.005), (0.005, 0.105)):
        mb.rod((x0, 0, 0.725), (x1, 0, 0.725), 0.009, 'M_BatWillow', seg=6)
    return mb


def cricket_bat():
    """0.85 m bat. Pivot at the grip (handle centre); blade hangs down -Z, flat face towards -Y."""
    mb = MB()
    mb.cylinder(0, 0, -0.12, 0.14, 0.017, 10, 'M_Rubber')             # rubber grip
    mb.cylinder(0, 0, 0.13, 0.15, 0.019, 10, 'M_Rubber')              # cap
    for k in range(4):                                                  # tape bands
        z = -0.1 + k * 0.06
        mb.cylinder(0, 0, z, z + 0.018, 0.0185, 10, 'M_LaundryRed')
    mb.cylinder(0, 0, -0.17, -0.12, 0.016, 8, 'M_BatWillow')
    z0, z1, hw = -0.70, -0.17, 0.054
    q = lambda z, w, ya, yb: [V(-w, ya, z), V(w, ya, z), V(w, yb, z), V(-w, yb, z)]
    mb.hexa(q(z0, hw * 0.8, -0.014, 0.006), q(z0 + 0.025, hw, -0.015, 0.01), 'M_BatWillow')         # toe
    mb.hexa(q(z0 + 0.025, hw, -0.015, 0.01), q(z1 - 0.07, hw, -0.015, 0.012), 'M_BatWillow')      # blade
    mb.hexa(q(z1 - 0.07, hw, -0.015, 0.012), q(z1, 0.02, -0.012, 0.012), 'M_BatWillow')           # shoulders
    mb.hexa(q(z0 + 0.08, 0.022, 0.009, 0.012), q(z1 - 0.1, 0.02, 0.009, 0.034), 'M_BatWillow')   # spine
    mb.box(-hw + 0.004, -0.0165, z0 + 0.32, hw - 0.004, -0.015, z0 + 0.42, 'M_Snack_03')
    return mb


def cricket_ball():
    mb = MB()
    r = 0.0325
    prof = [(0, -r)] + [(r * math.cos(-math.pi / 2 + math.pi * i / 8), r * math.sin(-math.pi / 2 + math.pi * i / 8)) for i in range(1, 8)] + [(0, r)]
    mb.revolve(prof, 14, 'M_TennisYellow')
    return mb


def wooden_bench(seed=4850):
    rng = random.Random(seed)
    mb = MB()
    L = 1.5
    mb.box(-L / 2, -0.17, 0.42, L / 2, 0.17, 0.46, 'M_WoodPlanks')
    mb.box(-L / 2 + 0.02, -0.16, 0.4, L / 2 - 0.02, -0.14, 0.42, 'M_WoodPlanks')
    for s in (-1, 1):
        x = s * (L / 2 - 0.15)
        for sy in (-1, 1):
            mb.beam((x, sy * 0.12, 0.42), (x + s * 0.03, sy * 0.15, 0.0), 0.05, 0.05, 'M_WoodPlanks')
        mb.box(x - 0.025, -0.13, 0.12, x + 0.025, 0.13, 0.16, 'M_WoodPlanks')
    mb.box(-L / 2 + 0.17, -0.02, 0.14, L / 2 - 0.17, 0.02, 0.18, 'M_WoodPlanks')
    for _ in range(3):
        nx = rng.uniform(-L / 2 + 0.1, L / 2 - 0.1)
        mb.box(nx - 0.01, -0.172, 0.43, nx + 0.01, -0.168, 0.45, 'M_Steel')
    return mb


def neon_sign(idx, w, h, vertical=False, seed=0):
    """Light-box shop sign. Horizontal: origin = bottom-centre at the wall (y=0); box projects towards -Y.
    Vertical (blade): sticks out perpendicular to the wall along -Y, faces +-X."""
    rng = random.Random(seed)
    mb = MB()
    slot = 'M_Neon_%02d' % idx
    if not vertical:
        dp = 0.16
        y0, y1 = -0.06 - dp, -0.06
        mb.box(-w / 2, y0, 0.0, w / 2, y1, h, 'M_Steel', skip=('-y',))
        o = V(-w / 2 + 0.03, y0, 0.03)
        mb.face([o, o + V(w - 0.06, 0, 0), o + V(w - 0.06, 0, h - 0.06), o + V(0, 0, h - 0.06)], slot, normal=(0, -1, 0),
                uvo=(o, Vector((1, 0, 0)), Vector((0, 0, 1)), w - 0.06, h - 0.06))
        # frame lip
        for (a, b, c, d) in ((-w / 2, 0, w / 2, 0.03), (-w / 2, h - 0.03, w / 2, h), (-w / 2, 0.03, -w / 2 + 0.03, h - 0.03),
                             (w / 2 - 0.03, 0.03, w / 2, h - 0.03)):
            mb.box(a, y0 - 0.015, b, c, y0, d, 'M_Steel')
        for x in (-w / 2 + 0.2, w / 2 - 0.2):
            for z in (0.1, h - 0.1):
                mb.box(x - 0.02, y1, z - 0.02, x + 0.02, 0.0, z + 0.02, 'M_MetalRust')
        # feed cable running up the wall from the box top
        mb.box(w / 2 - 0.12, -0.015, h, w / 2 - 0.108, -0.003, h + 0.35, 'M_Rubber')
    else:
        th = 0.12
        y_in, y_out = -0.25, -0.25 - w
        mb.box(-th / 2, y_out, 0.0, th / 2, y_in, h, 'M_Steel', skip=('-x', '+x'))
        for s in (-1, 1):
            x = s * th / 2
            if s > 0:
                o, u = V(x, y_out, 0.0), Vector((0, 1, 0))
            else:
                o, u = V(x, y_in, 0.0), Vector((0, -1, 0))
            mb.face([o, o + u * w, o + u * w + V(0, 0, h), o + V(0, 0, h)], slot, normal=(s, 0, 0),
                    uvo=(o, u, Vector((0, 0, 1)), w, h))
        # brackets to the wall
        for z in (0.15, h - 0.15):
            mb.box(-0.025, y_in, z - 0.025, 0.025, 0.0, z + 0.025, 'M_MetalRust')
            mb.box(-0.06, -0.01, z - 0.08, 0.06, 0.0, z + 0.08, 'M_MetalRust')
        mb.box(-th / 2 - 0.01, y_out - 0.01, h, th / 2 + 0.01, y_in + 0.01, h + 0.04, 'M_Steel')
        mb.box(-th / 2 - 0.01, y_out - 0.01, -0.04, th / 2 + 0.01, y_in + 0.01, 0.0, 'M_Steel')
    return mb


NEON = [(1, 1.5, 0.5, False), (2, 2.0, 0.6, False), (3, 2.5, 0.75, False), (4, 3.0, 0.9, False), (5, 0.6, 1.8, True),
        (6, 0.75, 2.2, True)]


def tarp_canopy(w, d, seed=0, h=2.6, ropes=True):
    """Blue tarp on bamboo poles. Origin = bottom-centre, canopy spans x in [-w/2, w/2], y in [-d/2, d/2]."""
    rng = random.Random(seed)
    mb = MB()
    poles = []
    xs = [-w / 2, w / 2] if w < 4 else [-w / 2, 0.0, w / 2]
    for x in xs:
        for y in (-d / 2, d / 2):
            hh = h + rng.uniform(-0.1, 0.15) + (0.25 if y > 0 else 0.0)
            poles.append((x, y, hh))
            mb.cylinder(x + rng.uniform(-0.03, 0.03), y, 0.0, hh, 0.035, 7, 'M_WoodPlanks')
    nx, ny = (10 if w < 4 else 14), 8
    ph = rng.uniform(0, 6)

    def hz(x, y):
        # interpolate pole heights along x for each edge, then along y
        def edge(yv):
            pts = sorted([(px, ph_) for (px, py, ph_) in poles if py == yv])
            for (a, b) in zip(pts[:-1], pts[1:]):
                if a[0] <= x <= b[0] + 1e-6:
                    return lerp(a[1], b[1], (x - a[0]) / (b[0] - a[0]))
            return pts[-1][1]
        t = (y + d / 2) / d
        return lerp(edge(-d / 2), edge(d / 2), t)
    rows = []
    ov = 0.2
    for i in range(nx + 1):
        col = []
        for j in range(ny + 1):
            s, t = i / nx, j / ny
            x = lerp(-w / 2 - ov, w / 2 + ov, s)
            y = lerp(-d / 2 - ov, d / 2 + ov, t)
            xc, yc = max(-w / 2, min(w / 2, x)), max(-d / 2, min(d / 2, y))
            seg = w / (len(xs) - 1)
            sx = ((xc + w / 2) % seg) / seg
            sag = 0.22 * math.sin(math.pi * sx) * (0.4 + 0.6 * math.sin(math.pi * (yc + d / 2) / d)) + \
                0.08 * math.sin(math.pi * (yc + d / 2) / d)
            z = hz(xc, yc) + 0.03 - sag
            # droop the overhanging hem
            z -= 0.6 * (abs(x - xc) + abs(y - yc))
            z += 0.015 * math.sin(ph + s * 13 + t * 9)
            col.append(V(x, y, z))
        rows.append(col)
    grid_faces(mb, rows, 'M_TarpBlue', (0, 0, 1), th=0.006)
    if ropes:
        for (x, y, hh) in poles:
            sx = 1 if x > 0 else -1 if x < 0 else 0
            sy = 1 if y > 0 else -1
            if sx == 0:
                continue
            g = V(x + sx * 0.7, y + sy * 0.7, 0.0)
            mb.beam((x, y, hh - 0.05), g, 0.008, 0.008, 'M_Whitewash')
            mb.boxc(g.x, g.y, 0.0, 0.04, 0.04, 0.15, 'M_WoodPlanks')
    return mb


def wire_bundle(seed=4900, L=6.0, z=5.0):
    rng = random.Random(seed)
    mb = MB()
    xa, xb = -L / 2, L / 2
    # twisted main bundle
    sag = 0.55
    n = 24
    for k in range(5):
        ph = k * math.tau / 5
        pts = []
        for i in range(n + 1):
            t = i / n
            c = V(lerp(xa, xb, t), 0.0, z - sag * 4 * t * (1 - t))
            a = ph + t * 14.0
            pts.append(c + V(0, 0.035 * math.cos(a), 0.035 * math.sin(a)))
        for p, q in zip(pts[:-1], pts[1:]):
            mb.beam(p, q, 0.014, 0.014, 'M_Rubber')
    # loose individual cables
    for k in range(9):
        ya, yb = rng.uniform(-0.45, 0.45), rng.uniform(-0.45, 0.45)
        za, zb = z + rng.uniform(-0.3, 0.4), z + rng.uniform(-0.3, 0.4)
        wire(mb, (xa + rng.uniform(-0.1, 0.3), ya, za), (xb - rng.uniform(-0.1, 0.3), yb, zb), rng.uniform(0.25, 1.1),
             r=rng.uniform(0.005, 0.01), n=14, mat='M_Rubber' if rng.random() < 0.8 else 'M_PlasticRed',
             wob=(0.0, 0.03, rng.uniform(0, 6)))
    # hanging drops and a coil
    for _ in range(3):
        t = rng.uniform(0.2, 0.8)
        p = V(lerp(xa, xb, t), rng.uniform(-0.1, 0.1), z - sag * 4 * t * (1 - t))
        wire(mb, p, p + V(rng.uniform(-0.4, 0.4), rng.uniform(-0.2, 0.2), -rng.uniform(0.6, 1.4)), 0.15, r=0.006, n=6)
    t = rng.uniform(0.3, 0.7)
    cp = V(lerp(xa, xb, t), 0.05, z - sag * 4 * t * (1 - t) - 0.25)
    for k in range(3):
        mb.add(torus(0.2 + 0.01 * k, 0.007, 14, 3), T(cp.x, cp.y + 0.01 * k, cp.z) @ Rx(90 + rng.uniform(-15, 15)))
    # junction box with a broken lid
    jx = lerp(xa, xb, 0.25)
    jz = z - sag * 4 * 0.25 * 0.75
    mb.box(jx - 0.1, -0.06, jz - 0.12, jx + 0.1, 0.06, jz + 0.05, 'M_Whitewash')
    return mb


# ===================================================================================== register
def register(add):
    B = 'origin = bottom-centre of the FRONT facade at street level (Z=0); facade faces -Y'
    for (name, seed, W, D, p) in SHANTY_1F:
        add(name, 'building_dharavi', (lambda seed=seed, W=W, D=D, p=p: (shanty(seed, W, D, p), [])), B,
            '%.1f x %.1f m one-storey Dharavi shanty, %s walls, %s roof, raised ota platform in front.' % (W, D, p['mat'], p.get('roof')))
    for (name, seed, W, D, p) in SHANTY_2F:
        add(name, 'building_dharavi', (lambda seed=seed, W=W, D=D, p=p: (shanty_2f(seed, W, D, p), [])), B,
            '%.1f x %.1f m two-storey shanty: ground %s, upper %s, external steel ladder to a railed balcony, laundry, tank.' %
            (W, D, p['mat'], p.get('upper')))
    for (name, seed, W, D, fl, p) in TENEMENTS:
        add(name, 'building_dharavi', (lambda seed=seed, W=W, D=D, fl=fl, p=p: (tenement(seed, W, D, fl, p), [])), B,
            '%.1f x %.1f m, %d storey self-built tenement, ground-floor shops (shutters, signboards), tin hoods, laundry, wires.'
            % (W, D, fl))
    for i, (W, D, H) in enumerate(((3.2, 3.0, 2.4), (4.5, 3.5, 2.6), (6.0, 4.0, 2.8), (3.8, 4.5, 2.5))):
        add('Shack_Corrugated_%02d' % (i + 1), 'building_dharavi', (lambda i=i, W=W, D=D, H=H: (corr_shack(4500 + i, W, D, H), [])), B,
            '%.1f x %.1f m rusty corrugated-sheet shack with tin door, sloped tin roof with stones.' % (W, D))
    add('Wall_Corrugated_6m', 'props_dharavi', lambda: (corr_wall(), []), 'origin = bottom-centre; runs along X; poster side faces -Y',
        '6 m fence of patched corrugated sheets on posts (~2.5 m high), sheets on both sides.')
    add('Gateway_Concrete', 'props_dharavi', lambda: (gateway(), []),
        'origin = bottom-centre of the opening; passage runs along Y (open), columns at x = +-1.83 m',
        'Crude concrete portal: 3.2 m clear opening, 2.9 m clear height, 0.6 m lintel, posters (M_Poster), name board (M_Signboard).')
    add('Laundry_Line_6m', 'props_dharavi', lambda: (laundry_line(6.0, 4710), []),
        'origin = ground point below mid-span; hooks at x = +-3 m, z = 3.2 m; rope along X', '8 garments, sag 0.25 m.',
        preview_dir=(-0.3, -1.0, 0.3))
    add('Laundry_Line_10m', 'props_dharavi', lambda: (laundry_line(10.0, 4711), []),
        'origin = ground point below mid-span; hooks at x = +-5 m, z = 3.2 m; rope along X', '14 garments, sag 0.42 m.',
        preview_dir=(-0.3, -1.0, 0.3))
    add('Chai_Stall', 'props_dharavi', lambda: (chai_stall(), []),
        'origin = bottom-centre of the counter front (y=0); customers at -Y, vendor stands at +Y',
        'Mumbai tapri: counter with M_Signboard face, jars, stove + pot, brass kettle, glasses, blue tarp roof, snack strips.')
    add('Snack_Strip', 'props_dharavi', lambda: (snack_strip_asset(), []),
        'origin = top hook point; strip hangs down 1.25 m along -Z', 'Strip of 16 snack sachets.', ground=False,
        preview_dir=(-0.4, -1.0, 0.2))
    add('Veg_Cart', 'props_dharavi', lambda: (veg_cart(), []), 'origin = bottom-centre; long axis X, push handles at -X',
        'Wooden handcart on bicycle wheels with tomatoes, onions, potatoes, beans and a balance scale.')
    add('Matka_Stack', 'props_dharavi', lambda: (matka_stack(), []), 'origin = bottom-centre', 'Clay pots on a plank, some stacked.')
    for k in (1, 2, 3):
        add('Sack_Pile_%02d' % k, 'props_dharavi', (lambda k=k: (sack_pile(k, 4840 + k), [])), 'origin = bottom-centre',
            ['', 'Heap of gunny / poly sacks ~1.2 m.', 'Stack of compressed recycling bales ~2.4 m.', 'Jumbo bags + sacks ~1.3 m.'][k])
    add('Drum_Blue', 'props_dharavi', lambda: (blue_drum(), []), 'origin = bottom-centre', 'Blue plastic 200 l water drum.')
    add('LPG_Cylinder', 'props_dharavi', lambda: (lpg(), []), 'origin = bottom-centre', 'Red 14.2 kg LPG cylinder.')
    add('Cricket_Stumps', 'props_dharavi', lambda: (cricket_stumps(), []), 'origin = bottom-centre; stumps in a row along X',
        'Three stumps + bails on a yellow base.')
    add('Cricket_Bat', 'props_dharavi', lambda: (cricket_bat(), []),
        'origin = grip (handle centre); blade hangs along -Z, face towards -Y', '0.85 m tape-wrapped street cricket bat.',
        ground=False)
    add('Cricket_Ball', 'props_dharavi', lambda: (cricket_ball(), []), 'origin = centre', '6.5 cm tennis ball.', ground=False)
    add('Plastic_Stool', 'props_dharavi', lambda: (stool('M_PlasticRed'), []), 'origin = bottom-centre', 'Red plastic stool.')
    add('Plastic_Stool_Blue', 'props_dharavi', lambda: (stool('M_PlasticBlue'), []), 'origin = bottom-centre', 'Blue plastic stool.')
    add('Wooden_Bench', 'props_dharavi', lambda: (wooden_bench(), []), 'origin = bottom-centre; long axis X', '1.5 m plank bench.')
    for (idx, w, h, vert) in NEON:
        add('Neon_Sign_%02d' % idx, 'props_dharavi', (lambda idx=idx, w=w, h=h, vert=vert: (neon_sign(idx, w, h, vert, idx), [])),
            ('origin = wall attachment point, bottom of the sign (wall plane y=0); blade sticks out along -Y, faces +-X'
             if vert else 'origin = bottom-centre at the wall plane (y=0); box projects 0.22 m towards -Y'),
            'Light-box sign, face slot M_Neon_%02d with 0..1 UVs.' % idx, ground=False,
            preview_dir=(-1.0, -0.5, 0.3) if vert else (-0.4, -1.0, 0.25))
    add('Tarp_Canopy_3m', 'props_dharavi', lambda: (tarp_canopy(3.0, 3.0, 4910), []), 'origin = bottom-centre',
        '3 x 3 m blue tarp on 4 bamboo poles with guy ropes.')
    add('Tarp_Canopy_5m', 'props_dharavi', lambda: (tarp_canopy(5.0, 4.0, 4911), []), 'origin = bottom-centre',
        '5 x 4 m blue tarp on 6 bamboo poles with guy ropes.')
    add('Wire_Bundle_Alley', 'props_dharavi', lambda: (wire_bundle(), []),
        'origin = ground point below mid-span; cables span x = +-3 m at z ~ 5 m', 'Twisted bundle + loose cables, drops, coil.',
        preview_dir=(-0.3, -1.0, 0.3))
