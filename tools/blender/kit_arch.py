"""
kit_arch.py - reusable Indian / Varanasi architectural components built on kit_core.MB.

Facade frame convention (used by facade_wall / openings / jharokha / balcony):
    u = X (along facade, left->right seen from the river), v = Z (up),
    wall plane at Y = 0, outward = -Y, into the wall = +Y.
"""
import math
from mathutils import Vector
from kit_core import MB, V, T, Rz, Rx, S, TAU, ccw, area2d, regular_poly, lerp

# ======================================================================= arches / outlines

def arch_curve(kind, x0, x1, zs, seg=12):
    """Arch intrados from left springer (x0, zs) to right springer (x1, zs), passing over the top."""
    w = x1 - x0
    cx = (x0 + x1) / 2
    r = w / 2
    pts = []
    if kind in ('arch', 'semi'):
        for i in range(seg + 1):
            a = math.pi - math.pi * i / seg
            pts.append((cx + r * math.cos(a), zs + r * math.sin(a)))
    elif kind == 'cusped':
        n = max(seg, 20)
        for i in range(n + 1):
            a = math.pi - math.pi * i / n
            rr = r * (1.0 - 0.13 * abs(math.sin(a * 2.5)) ** 0.7)
            pts.append((cx + rr * math.cos(a), zs + rr * math.sin(a) * 1.08))
    elif kind == 'pointed':
        R = 0.82 * w
        half = seg // 2
        # left half: circle centred at (x0 + R, zs) ; right half: centred at (x1 - R, zs)
        apex_z = zs + math.sqrt(max(R * R - (R - r) ** 2, 0))
        for i in range(half + 1):
            x = x0 + r * i / half
            z = zs + math.sqrt(max(R * R - (x - (x0 + R)) ** 2, 0))
            pts.append((x, min(z, apex_z)))
        for i in range(1, half + 1):
            x = cx + r * i / half
            z = zs + math.sqrt(max(R * R - (x - (x1 - R)) ** 2, 0))
            pts.append((x, min(z, apex_z)))
    elif kind == 'flat':
        pts = [(x0, zs), (x1, zs)]
    else:
        raise ValueError(kind)
    pts[0] = (x0, zs)
    pts[-1] = (x1, zs)
    return pts


def arch_rise(kind, w):
    if kind in ('arch', 'semi'):
        return w / 2
    if kind == 'cusped':
        return w / 2 * 1.08
    if kind == 'pointed':
        R = 0.82 * w
        return math.sqrt(R * R - (R - w / 2) ** 2)
    return 0.0


def outline(kind, cx, sill, w, h, seg=12):
    """Opening outline (u, v) CCW seen from the front. h = total height including arch."""
    x0, x1 = cx - w / 2, cx + w / 2
    if kind == 'rect':
        return [(x0, sill), (x1, sill), (x1, sill + h), (x0, sill + h)]
    rise = arch_rise(kind, w)
    zs = sill + max(h - rise, 0.05)
    curve = arch_curve(kind, x0, x1, zs, seg)
    pts = [(x0, sill), (x1, sill)] + list(reversed(curve))
    # remove duplicate consecutive
    out = []
    for p in pts:
        if not out or abs(out[-1][0] - p[0]) + abs(out[-1][1] - p[1]) > 1e-6:
            out.append(p)
    if abs(out[0][0] - out[-1][0]) + abs(out[0][1] - out[-1][1]) < 1e-6:
        out.pop()
    return ccw(out)


def _loop_extrude(mb, loop, ya, yb, mat, outward):
    n = len(loop)
    for i in range(n):
        a = loop[i]
        b = loop[(i + 1) % n]
        du, dv = b[0] - a[0], b[1] - a[1]
        nu, nv = dv, -du
        if not outward:
            nu, nv = -nu, -nv
        mb.face([V(a[0], ya, a[1]), V(b[0], ya, b[1]), V(b[0], yb, b[1]), V(a[0], yb, a[1])], mat,
                normal=(nu, 0, nv))


def opening(mb, op, wall_mat):
    """Build one recessed opening in facade frame. Returns the hole outline for the wall face."""
    kind = op.get('kind', 'rect')
    cx, sill, w, h = op['cx'], op['sill'], op['w'], op['h']
    seg = op.get('seg', 12)
    O = outline(kind, cx, sill, w, h, seg)
    fw = op.get('fw', 0.0)
    fd = op.get('fd', 0.04)
    fmat = op.get('frame_mat', wall_mat)
    rmat = op.get('reveal_mat', fmat if fw > 0 else wall_mat)
    depth = op.get('depth', 0.3)
    back = op.get('back_mat', 'M_WindowDark')
    if fw > 0:
        O2 = outline(kind, cx, sill - fw, w + 2 * fw, h + 2 * fw, seg)
        mb.face_holes([V(u, -fd, v) for u, v in O2], [[V(u, -fd, v) for u, v in O]], (0, -1, 0), fmat)
        _loop_extrude(mb, O2, 0.0, -fd, fmat, outward=True)
        hole = O2
        y0 = -fd
    else:
        hole = O
        y0 = 0.0
    if op.get('reveal', True):
        _loop_extrude(mb, O, y0, depth, rmat, outward=False)
    if back:
        mb.face_holes([V(u, depth, v) for u, v in O], [], (0, -1, 0), back)
    rect_top = sill + (h if kind == 'rect' else max(h - arch_rise(kind, w), 0.05))
    fill = op.get('fill')
    if fill == 'bars':
        n = max(2, int(w / 0.13))
        yb = min(depth * 0.35, 0.12)
        for i in range(1, n):
            x = cx - w / 2 + w * i / n
            mb.box(x - 0.009, yb - 0.009, sill, x + 0.009, yb + 0.009, rect_top, 'M_MetalRust')
        for zz in (sill + (rect_top - sill) * 0.5,):
            mb.box(cx - w / 2, yb - 0.012, zz - 0.015, cx + w / 2, yb + 0.012, zz + 0.015, 'M_MetalRust')
    elif fill == 'shutters' and kind == 'rect':
        pw = w / 2
        for sgn in (-1, 1):
            xa = cx + sgn * (w / 2 + fw + 0.02)
            xb = xa + sgn * pw
            mb.box(min(xa, xb), -fd - 0.05, sill + 0.02, max(xa, xb), -fd - 0.015, rect_top - 0.02, 'M_WoodShutter')
    elif fill == 'half_shutter':
        mb.box(cx, depth * 0.5, sill, cx + w / 2, depth * 0.5 + 0.03, rect_top, 'M_WoodShutter')
    elif fill == 'glass_grid':
        yb = depth * 0.4
        mb.box(cx - 0.02, yb, sill, cx + 0.02, yb + 0.04, rect_top, 'M_WoodShutter')
        mb.box(cx - w / 2, yb, (sill + rect_top) / 2 - 0.02, cx + w / 2, yb + 0.04, (sill + rect_top) / 2 + 0.02, 'M_WoodShutter')
    if op.get('ledge') and kind != 'door':
        e = 0.06
        mb.box(cx - w / 2 - fw - e, -fd - 0.07, sill - fw - 0.07, cx + w / 2 + fw + e, 0.0, sill - fw,
               op.get('ledge_mat', fmat))
    if op.get('hood'):
        hm = op.get('hood_mat', fmat)
        top = sill + h + fw
        hw = w / 2 + fw + 0.12
        dp = op.get('hood_depth', 0.45)
        mb.hexa([(cx - hw, 0, top + 0.08), (cx + hw, 0, top + 0.08), (cx + hw, -dp, top - 0.06), (cx - hw, -dp, top - 0.06)],
                [(cx - hw, 0, top + 0.16), (cx + hw, 0, top + 0.16), (cx + hw, -dp, top + 0.0), (cx - hw, -dp, top + 0.0)], hm)
        for sgn in (-1, 1):
            bx = cx + sgn * (hw - 0.1)
            mb.hexa([(bx - 0.04, 0, top - 0.25), (bx + 0.04, 0, top - 0.25), (bx + 0.04, -0.06, top - 0.25), (bx - 0.04, -0.06, top - 0.25)],
                    [(bx - 0.04, 0, top + 0.08), (bx + 0.04, 0, top + 0.08), (bx + 0.04, -dp * 0.8, top + 0.0), (bx - 0.04, -dp * 0.8, top + 0.0)], hm)
    return hole


def facade_wall(mb, x0, x1, z0, z1, openings, wall_mat):
    """Wall rectangle in facade frame with recessed openings."""
    holes = []
    for op in openings:
        hole = opening(mb, op, wall_mat)
        us = [p[0] for p in hole]
        vs = [p[1] for p in hole]
        if min(us) <= x0 + 1e-3 or max(us) >= x1 - 1e-3 or min(vs) <= z0 + 1e-3 or max(vs) >= z1 - 1e-3:
            raise ValueError('opening outside wall %s' % op)
        holes.append(hole)
    outer = [V(x0, 0, z0), V(x1, 0, z0), V(x1, 0, z1), V(x0, 0, z1)]
    mb.face_holes(outer, [[V(u, 0, v) for u, v in h] for h in holes], (0, -1, 0), wall_mat)


def fits(op, x0, x1, z0, z1, margin=0.03):
    fw = op.get('fw', 0.0)
    w = op['w'] + 2 * fw
    return (op['cx'] - w / 2 > x0 + margin and op['cx'] + w / 2 < x1 - margin and
            op['sill'] - fw > z0 + margin and op['sill'] + op['h'] + fw < z1 - margin)


def arch_panel(mb, x0, x1, zs, zt, t, mat, kind='cusped', seg=14, soffit_mat=None):
    """Solid spandrel: rectangle [x0,x1]x[zs,zt] minus an arch springing at zs; thickness t centred on y=0."""
    curve = arch_curve(kind, x0, x1, zs, seg)
    poly = [(x0, zt)] + curve + [(x1, zt)]
    # poly: top-left, down to left springer, over arch, right springer, top-right
    for y, n in ((-t / 2, (0, -1, 0)), (t / 2, (0, 1, 0))):
        mb.face_holes([V(u, y, v) for u, v in poly], [], n, mat)
    # soffit (arch underside) + top + ends
    sm = soffit_mat or mat
    for i in range(len(curve) - 1):
        a, b = curve[i], curve[i + 1]
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        c = ((x0 + x1) / 2, zs)
        mb.face([V(a[0], -t / 2, a[1]), V(b[0], -t / 2, b[1]), V(b[0], t / 2, b[1]), V(a[0], t / 2, a[1])], sm,
                normal=(c[0] - mid[0], 0, c[1] - mid[1]))
    mb.face([V(x0, -t / 2, zt), V(x1, -t / 2, zt), V(x1, t / 2, zt), V(x0, t / 2, zt)], mat, normal=(0, 0, 1))


# ======================================================================= profiles

PROF_BAND = [(0, -0.12), (0.05, -0.12), (0.05, 0.0), (0.08, 0.02), (0.08, 0.08), (0, 0.08)]
PROF_BAND_SMALL = [(0, -0.06), (0.04, -0.06), (0.04, 0.05), (0, 0.05)]
PROF_CORNICE = [(0, -0.45), (0.05, -0.45), (0.05, -0.35), (0.1, -0.32), (0.14, -0.22), (0.22, -0.16),
                (0.3, -0.1), (0.3, 0.0), (0.34, 0.0), (0.34, 0.08), (0, 0.08)]
PROF_CHHAJJA = [(0, -0.05), (0.08, -0.12), (0.62, -0.32), (0.62, -0.26), (0.08, 0.02), (0, 0.06)]
PROF_PLINTH = [(0.12, 0.0), (0.12, 0.25), (0.06, 0.32), (0.06, 0.45), (0, 0.5)]
PROF_COPING = [(0, 0), (0.04, 0), (0.04, 0.07), (0, 0.07)]


def scaled_profile(prof, sd=1.0, sh=1.0):
    return [(d * sd, h * sh) for d, h in prof]


# ======================================================================= small ornaments

def kalash(scale=1.0, mat='M_Gold', seg=12):
    mb = MB()
    prof = [(0, 0), (0.07, 0), (0.13, 0.05), (0.14, 0.11), (0.09, 0.17), (0.05, 0.2), (0.08, 0.23),
            (0.1, 0.26), (0.05, 0.3), (0.03, 0.36), (0.05, 0.4), (0.03, 0.45), (0.012, 0.52), (0, 0.6)]
    mb.revolve([(r * scale, z * scale) for r, z in prof], seg, mat)
    return mb


def amalaka(r, mat, seg=32):
    mb = MB()
    prof = [(0, 0), (0.55, 0), (0.92, 0.1), (1.0, 0.22), (0.92, 0.36), (0.55, 0.45), (0, 0.45)]
    mb.revolve([(a * r, b * r) for a, b in prof], seg, mat, lobe=lambda th: 1 + 0.07 * abs(math.cos(8 * th)))
    return mb


def flag(length=1.2, height=0.8, mat='M_Saffron', seed=0, triangular=True, nx=8, nz=4):
    """Pennant in XZ plane hanging from x=0 (pole side), flying towards +X. Two-sided thin sheet."""
    mb = MB()
    grid = []
    for i in range(nx + 1):
        s = i / nx
        hh = height * (1 - s * 0.85) if triangular else height
        col = []
        for j in range(nz + 1):
            t = j / nz
            z = -hh * t + (height - hh) * 0.0
            y = 0.06 * math.sin(s * 5.0 + seed) * s + 0.02 * math.sin(t * 3 + seed) * s
            col.append(V(length * s, y, z - (height - hh) * 0.5 * 0))
        grid.append(col)
    for i in range(nx):
        for j in range(nz):
            q = [grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]]
            mb._add([p.copy() for p in q], mat)
            mb._add([p + Vector((0, 0.004, 0)) for p in reversed(q)], mat)
    return mb


def flag_pole(height=6.0, flag_len=1.4, flag_h=0.9, pole_mat='M_WoodPlanks', flag_mat='M_Saffron', seed=0, r=0.035):
    mb = MB()
    mb.cylinder(0, 0, 0, height, r, 8, pole_mat, r_top=r * 0.6)
    f = flag(flag_len, flag_h, flag_mat, seed)
    mb.add(f, T(0, 0, height - 0.05) @ Rz(20 + seed * 37 % 90))
    return mb


def dome(R, mat, style='onion', seg=24, finial_mat='M_Gold', finial=True, lobed=False, drum_h=0.0, drum_mat=None):
    mb = MB()
    if style == 'onion':
        prof = [(0.9, 0.0), (1.0, 0.08), (1.06, 0.2), (1.05, 0.32), (0.98, 0.45), (0.84, 0.58), (0.64, 0.7),
                (0.42, 0.8), (0.22, 0.88), (0.1, 0.94), (0.05, 1.0)]
        H = 1.35 * R
    elif style == 'bulb':
        prof = [(0.95, 0.0), (1.0, 0.1), (1.0, 0.3), (0.92, 0.5), (0.72, 0.68), (0.45, 0.83), (0.18, 0.94), (0.05, 1.0)]
        H = 1.1 * R
    else:  # hemispherical
        prof = [(1.0, 0.0), (0.98, 0.18), (0.92, 0.38), (0.8, 0.58), (0.6, 0.78), (0.33, 0.93), (0.05, 1.0)]
        H = 1.0 * R
    z0 = drum_h
    if drum_h > 0:
        mb.cylinder(0, 0, 0, drum_h, R * 0.95, seg, drum_mat or mat, caps=False)
        mb.revolve([(R * 0.95, drum_h), (R * 1.08, drum_h), (R * 1.08, drum_h + 0.06 * R), (R * 0.9, drum_h + 0.06 * R)], seg, drum_mat or mat)
    lobe = (lambda th: 1 + 0.035 * abs(math.cos(8 * th))) if lobed else None
    mb.revolve([(0, z0)] + [(r * R, z0 + z * H) for r, z in prof], seg, mat, lobe=lobe)
    # lotus crown ring
    mb.revolve([(0.05 * R, z0 + H), (0.14 * R, z0 + H + 0.03 * R), (0.1 * R, z0 + H + 0.08 * R), (0.0, z0 + H + 0.09 * R)], 12, mat)
    if finial:
        mb.add(kalash(R * 0.9, finial_mat), T(0, 0, z0 + H + 0.08 * R))
    return mb


def pyramid_roof(sx, sy, h, mat, overhang=0.1, steps=0):
    """Hipped / pyramidal roof on footprint centred at origin, base at z=0."""
    mb = MB()
    ax, ay = sx / 2 + overhang, sy / 2 + overhang
    if steps <= 0:
        base = [V(-ax, -ay, 0), V(ax, -ay, 0), V(ax, ay, 0), V(-ax, ay, 0)]
        top = V(0, 0, h)
        c = V(0, 0, h * 0.3)
        for i in range(4):
            mb.face([base[i], base[(i + 1) % 4], top], mat, center=c)
        mb.face(base, mat, normal=(0, 0, -1))
    else:
        for k in range(steps):
            t0 = k / steps
            f = 1 - t0 * 0.85
            mb.box(-ax * f, -ay * f, h * t0, ax * f, ay * f, h * (t0 + 1.0 / steps) - 0.02, mat)
    return mb


# ======================================================================= shikhara (Nagara)

def _shikhara_lobe(th):
    c, s = abs(math.cos(th)), abs(math.sin(th))
    sq = 1.0 / max(c, s)
    sq = min(sq, 1.22)  # chamfered corners
    # angular distance to nearest face centre (0, 90, 180, 270 deg)
    a = (th + math.pi / 4) % (math.pi / 2) - math.pi / 4
    a = abs(a)
    proj = 0.0
    if a < math.radians(10):
        proj = 0.16
    elif a < math.radians(22):
        proj = 0.09
    elif a < math.radians(32):
        proj = 0.035
    return sq * 0.86 + proj


def shikhara(half, H, mat, top_mat=None, band_mat=None, seg=64, urus=True, kalash_mat='M_Gold',
             flag_mat='M_Saffron', seed=0, with_flag=True):
    """Curvilinear Nagara spire on a square base of half-size `half`, base at z=0, total spire height H
    (amalaka + kalash added on top)."""
    mb = MB()
    prof = []
    nb = max(8, int(H / 0.32))
    for i in range(nb + 1):
        t = i / nb
        r = half * (1.0 + 0.04 * math.sin(math.pi * min(t * 1.6, 1.0)) - 0.6 * t ** 2.3)
        z = H * t
        if i == 0:
            prof.append((r, z))
            continue
        # horizontal courses: small recess at each band
        zp = prof[-1][1]
        rec = 0.955 if i % 3 == 0 else 0.985
        prof.append((r * rec, zp + (z - zp) * 0.12))
        prof.append((r, zp + (z - zp) * 0.28))
        prof.append((r, z))
    prof.append((half * 0.34, H + 0.02))
    prof.append((half * 0.26, H + 0.12))
    prof.append((0, H + 0.12))
    tm = top_mat or mat

    def matfn(i, a, b):
        if band_mat and (i % 9 in (1,)):
            return band_mat
        return tm if a[1] > H * 0.72 else mat

    mb.revolve(prof, seg, mat, lobe=_shikhara_lobe, phase=math.pi / 4 * 0, matfn=matfn)
    zt = H + 0.1
    ar = half * 0.5
    mb.add(amalaka(ar, tm), T(0, 0, zt))
    mb.add(kalash(ar * 1.1, kalash_mat), T(0, 0, zt + ar * 0.45))
    if with_flag:
        ph = zt + ar * 0.45 + ar * 0.6
        fp = flag_pole(height=max(1.2, H * 0.14), flag_len=max(0.8, H * 0.1), flag_h=max(0.5, H * 0.06), pole_mat='M_WoodPlanks',
                       flag_mat=flag_mat, seed=seed, r=0.025)
        mb.add(fp, T(0, 0, ph - 0.2))
    if urus:
        # urushringa: half-spires clinging to the four faces
        for k in range(4):
            sub = shikhara(half * 0.42, H * 0.42, mat, top_mat, None, seg=32, urus=False, kalash_mat=kalash_mat,
                           with_flag=False)
            mb.add(sub, Rz(90 * k) @ T(0, -half * 0.82, H * 0.08))
        # corner mini spires
        for k in range(4):
            sub = shikhara(half * 0.26, H * 0.24, mat, top_mat, None, seg=24, urus=False, kalash_mat=kalash_mat,
                           with_flag=False)
            mb.add(sub, Rz(45 + 90 * k) @ T(0, -half * 0.98, 0))
    return mb


# ======================================================================= chhatri pavilion

def chhatri(size=2.2, n_sides=4, height=2.2, pillar_mat='M_Sandstone', dome_mat='M_Sandstone', base_mat=None,
            dome_style='hemi', finial_mat='M_Gold', seg=24, arches=True, plinth_h=0.3, chhajja_mat=None):
    """Rooftop chhatri. Centred at origin, base z=0."""
    mb = MB()
    bm = base_mat or pillar_mat
    cm = chhajja_mat or pillar_mat
    R = size / 2
    if n_sides == 4:
        mb.boxc(0, 0, 0, size + 0.2, size + 0.2, plinth_h, bm)
        pts = [(-R + 0.12, -R + 0.12), (R - 0.12, -R + 0.12), (R - 0.12, R - 0.12), (-R + 0.12, R - 0.12)]
    else:
        poly = regular_poly(n_sides, R / math.cos(math.pi / n_sides) + 0.1, phase=math.pi / n_sides)
        mb.prism(poly, 0, plinth_h, bm)
        pts = regular_poly(n_sides, (R - 0.1) / math.cos(math.pi / n_sides), phase=math.pi / n_sides)
    z0 = plinth_h
    zc = z0 + height
    pw = max(0.14, size * 0.08)
    for (x, y) in pts:
        # pillar: base block, octagonal-ish shaft (box), capital
        mb.boxc(x, y, z0, pw * 1.5, pw * 1.5, z0 + 0.18, pillar_mat)
        mb.cylinder(x, y, z0 + 0.18, zc - 0.25, pw * 0.55, 8, pillar_mat, caps=False)
        mb.boxc(x, y, zc - 0.25, pw * 1.4, pw * 1.4, zc - 0.1, pillar_mat)
        mb.boxc(x, y, zc - 0.1, pw * 1.7, pw * 1.7, zc, pillar_mat)
    # lintels + arches between pillars
    n = len(pts)
    for i in range(n):
        a = Vector((*pts[i], 0))
        b = Vector((*pts[(i + 1) % n], 0))
        d = b - a
        L = d.length
        mid = (a + b) / 2
        ang = math.degrees(math.atan2(d.y, d.x))
        sub = MB()
        if arches:
            arch_panel(sub, -L / 2 + pw * 0.6, L / 2 - pw * 0.6, zc - 0.25 - (L - pw * 1.2) * 0.45, zc, pw * 0.8,
                       pillar_mat, 'cusped', 14)
        sub.box(-L / 2, -pw * 0.45, zc - 0.02, L / 2, pw * 0.45, zc + 0.18, pillar_mat)
        # place: sub frame u along edge, normal -Y should face outward
        M = T(mid.x, mid.y, 0) @ Rz(ang)
        mb.add(sub, M)
    # chhajja ring (sloped eave)
    if n_sides == 4:
        ring = [(-R, -R), (R, -R), (R, R), (-R, R)]
    else:
        ring = regular_poly(n_sides, R / math.cos(math.pi / n_sides), phase=math.pi / n_sides)
    prof = [(0.0, 0.0), (0.05, -0.02), (size * 0.2, -0.16), (size * 0.2, -0.1), (0.04, 0.08), (0.0, 0.12)]
    mb.sweep_path(ring, prof, cm, closed=True, z0=zc + 0.2)
    # roof slab + drum + dome
    if n_sides == 4:
        mb.boxc(0, 0, zc + 0.18, size, size, zc + 0.36, dome_mat)
    else:
        mb.prism(ring, zc + 0.18, zc + 0.36, dome_mat)
    dm = dome(R * 0.92, dome_mat, style=dome_style, seg=seg, finial_mat=finial_mat, drum_h=0.12, lobed=True)
    mb.add(dm, T(0, 0, zc + 0.36))
    # inner ceiling (dark-ish underside) so it doesn't look hollow
    mb.face([V(p[0], p[1], zc + 0.18) for p in ring], dome_mat, normal=(0, 0, -1))
    return mb


# ======================================================================= jharokha / balconies

def corbels(mb, xs, dp, drop, mat, w=0.16):
    """Stepped brackets under a projection: at each x, 3 stacked blocks from wall (y=0) to -dp, below z=0."""
    for x in xs:
        for k in range(3):
            f = 1.0 - k * 0.33
            mb.box(x - w / 2, -dp * f, -drop * (k + 1) / 3, x + w / 2, 0.0, -drop * k / 3, mat)
        # pendant drop
        mb.box(x - w * 0.3, -dp * 0.95, -drop * 0.55, x + w * 0.3, -dp * 0.75, -0.01, mat)


def jharokha(w=2.0, h=2.2, dp=0.85, n_arches=3, roof='bangla', body_mat='M_SandstoneRed',
             trim_mat='M_Sandstone', roof_mat=None, dome_mat=None, arch_kind='cusped', seed=0):
    """Enclosed projecting balcony window. Local frame: wall plane y=0, projects to -Y,
    centred on x=0, z=0 = underside of base slab."""
    mb = MB()
    rm = roof_mat or body_mat
    hw = w / 2
    # brackets
    xs = [-hw + 0.2, hw - 0.2] if w < 1.8 else [-hw + 0.2, 0.0, hw - 0.2]
    corbels(mb, xs, dp, 0.75, trim_mat)
    # base slab with moulding
    mb.box(-hw - 0.08, -dp - 0.08, 0.0, hw + 0.08, 0.0, 0.16, trim_mat, skip=('+y',))
    # body shell (front + sides) with arched openings
    zb, zt = 0.16, h
    # front
    sub = MB()
    ops = []
    pil = 0.13
    aw = (w - pil * (n_arches + 1)) / n_arches
    for i in range(n_arches):
        cx = -hw + pil + aw / 2 + i * (aw + pil)
        ops.append(dict(kind=arch_kind, cx=cx, sill=0.75, w=aw, h=zt - 0.2 - 0.75, depth=0.08, fw=0.0,
                        back_mat='M_WindowDark', seg=14))
    facade_wall(sub, -hw, hw, zb, zt, ops, body_mat)
    mb.add(sub, T(0, -dp, 0))
    for sgn in (-1, 1):
        sub = MB()
        ops = [dict(kind=arch_kind, cx=0.0, sill=0.75, w=max(dp - 0.34, 0.25), h=zt - 0.2 - 0.75, depth=0.06,
                    back_mat='M_WindowDark', seg=12)]
        facade_wall(sub, -dp / 2, dp / 2, zb, zt, ops, body_mat)
        mb.add(sub, T(sgn * hw, -dp / 2, 0) @ Rz(90 * sgn))
    # parapet band on body (lower rail moulding) & chhajja
    mb.sweep_path([(-hw, 0), (-hw, -dp), (hw, -dp), (hw, 0)], [(0, 0), (0.04, 0.0), (0.04, 0.06), (0, 0.06)],
                  trim_mat, closed=False, z0=0.7)
    mb.sweep_path([(-hw, 0), (-hw, -dp), (hw, -dp), (hw, 0)],
                  [(0.0, 0.0), (0.04, -0.02), (0.36, -0.2), (0.36, -0.14), (0.04, 0.06), (0.0, 0.1)],
                  trim_mat, closed=False, z0=zt)
    # roof
    ztop = zt + 0.1
    if roof == 'bangla':
        nx, ny = 12, 8
        D = dp + 0.1
        hr = 0.55
        grid = []
        for i in range(nx + 1):
            s = -1 + 2 * i / nx
            row = []
            for j in range(ny + 1):
                u = -1 + 2 * j / ny
                zz = ztop + hr * math.sqrt(max(1 - u * u, 0)) * (1 - 0.3 * s * s) + 0.12 * (1 - abs(u) ** 2) * 0
                row.append(V(s * (hw + 0.05) * (1 - 0.02 * abs(u)), -D / 2 + u * D / 2 * 0.98, zz))
            grid.append(row)
        for i in range(nx):
            for j in range(ny):
                q = [grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]]
                mb.face(q, rm, normal=(0, 0, 1))
        # gable end caps
        for i, n in ((0, (-1, 0, 0)), (nx, (1, 0, 0))):
            pts = [grid[i][j] for j in range(ny + 1)]
            mb.face_holes(pts, [], n, rm)
        # ridge finials
        for s in (-0.7, 0.0, 0.7):
            zz = ztop + hr * (1 - 0.3 * s * s)
            mb.add(kalash(0.35, 'M_Gold' if s == 0 else rm), T(s * hw, -D / 2, zz - 0.02))
    elif roof == 'dome':
        mb.box(-hw, -dp, ztop - 0.1, hw, 0, ztop + 0.05, rm, skip=('+y',))
        dm = dome(min(hw, dp / 2) * 0.85, dome_mat or rm, style='onion', seg=20, lobed=True)
        mb.add(dm, T(0, -dp / 2, ztop + 0.05))
    else:
        mb.box(-hw, -dp, ztop - 0.1, hw, 0, ztop + 0.1, rm, skip=('+y',))
        for x in (-hw + 0.1, hw - 0.1):
            mb.boxc(x, -dp + 0.1, ztop + 0.1, 0.12, 0.12, ztop + 0.35, rm)
    return mb


def balcony(w=3.0, dp=1.1, style='balusters', slab_mat='M_Sandstone', rail_mat='M_Sandstone',
            bracket_mat=None, cloth=None, seed=0):
    """Open balcony: slab top at z=0, projecting to -Y from wall plane y=0, centred on x=0."""
    mb = MB()
    hw = w / 2
    bm = bracket_mat or slab_mat
    mb.box(-hw, -dp, -0.16, hw, 0.0, 0.0, slab_mat, skip=('+y',))
    mb.sweep_path([(-hw, 0), (-hw, -dp), (hw, -dp), (hw, 0)], [(0, 0), (0.05, 0), (0.05, 0.05), (0, 0.07)],
                  slab_mat, closed=False, z0=-0.16)
    n = max(2, int(w / 1.3) + 1)
    corbels(mb, [-hw + 0.15 + (w - 0.3) * i / (n - 1) for i in range(n)], dp * 0.9, 0.5, bm, w=0.14)
    rh = 0.95
    path = [(-hw + 0.04, -0.0), (-hw + 0.04, -dp + 0.04), (hw - 0.04, -dp + 0.04), (hw - 0.04, 0.0)]
    if style == 'solid':
        t = 0.1
        mb.box(-hw, -dp, 0, hw, -dp + t, rh, rail_mat)
        for sgn in (-1, 1):
            x = sgn * hw
            mb.box(min(x, x - sgn * t), -dp + t, 0, max(x, x - sgn * t), 0, rh, rail_mat, skip=('+y',))
        mb.box(-hw - 0.03, -dp - 0.03, rh, hw + 0.03, -dp + t + 0.03, rh + 0.06, rail_mat)
    else:
        post_w = 0.06 if style == 'balusters' else 0.018
        spacing = 0.16 if style == 'balusters' else 0.12
        rm = rail_mat if style == 'balusters' else 'M_MetalRust'
        for (a, b) in zip(path[:-1], path[1:]):
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            k = max(1, int(L / spacing))
            for i in range(k + 1):
                t = i / k
                x = lerp(a[0], b[0], t)
                y = lerp(a[1], b[1], t)
                if style == 'balusters':
                    mb.cylinder(x, y, 0.05, rh - 0.05, post_w / 2, 6, rm, caps=False)
                else:
                    mb.box(x - post_w / 2, y - post_w / 2, 0.05, x + post_w / 2, y + post_w / 2, rh - 0.04, rm)
            # rails
            rw = 0.08 if style == 'balusters' else 0.04
            mb.beam((a[0], a[1], rh - 0.02), (b[0], b[1], rh - 0.02), rw, 0.06, rm)
            mb.beam((a[0], a[1], 0.05), (b[0], b[1], 0.05), rw, 0.05, rm)
        for (x, y) in path:
            mb.boxc(x, y, 0, 0.1, 0.1, rh + 0.02, rail_mat if style == 'balusters' else 'M_MetalRust')
    if cloth:
        # laundry: sari draped over the front rail
        import random
        rng = random.Random(seed)
        cw = min(w * 0.4, 1.4)
        cx = rng.uniform(-hw + cw / 2 + 0.1, hw - cw / 2 - 0.1)
        L = rng.uniform(0.6, 1.1)
        nx, nz = 6, 4
        grid = []
        for i in range(nx + 1):
            col = []
            for j in range(nz + 1):
                x = cx - cw / 2 + cw * i / nx
                z = rh - L * j / nz
                y = -dp - 0.03 - 0.03 * math.sin(i * 1.3 + seed) * (j / nz)
                col.append(V(x, y, z))
            grid.append(col)
        for i in range(nx):
            for j in range(nz):
                q = [grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]]
                mb.face(q, cloth, normal=(0, -1, 0))
                mb.face([p + Vector((0, 0.006, 0)) for p in q], cloth, normal=(0, 1, 0))
    return mb


def chhajja_x(mb, x0, x1, z, mat, dp=0.6, brackets=True, y0=0.0):
    """Continuous sloped sunshade along a facade at height z (top at wall)."""
    prof = [(0.0, -0.02), (0.06, -0.08), (dp, -0.3), (dp, -0.24), (0.06, 0.04), (0.0, 0.08)]
    mb.sweep_path([(x0, y0), (x1, y0)], prof, mat, closed=False, z0=z)
    if brackets:
        n = max(2, int((x1 - x0) / 1.6) + 1)
        for i in range(n):
            x = lerp(x0 + 0.15, x1 - 0.15, i / (n - 1))
            mb.hexa([(x - 0.05, y0, z - 0.45), (x + 0.05, y0, z - 0.45), (x + 0.05, y0 - 0.06, z - 0.45), (x - 0.05, y0 - 0.06, z - 0.45)],
                    [(x - 0.05, y0, z - 0.05), (x + 0.05, y0, z - 0.05), (x + 0.05, y0 - dp * 0.8, z - 0.25), (x - 0.05, y0 - dp * 0.8, z - 0.25)], mat)


# ======================================================================= rooftop clutter

def water_tank(kind='plastic', r=0.55, h=1.1, stand=0.0):
    mb = MB()
    z0 = 0.0
    if stand > 0:
        for sx in (-1, 1):
            for sy in (-1, 1):
                mb.box(sx * r * 0.7 - 0.04, sy * r * 0.7 - 0.04, 0, sx * r * 0.7 + 0.04, sy * r * 0.7 + 0.04, stand, 'M_MetalRust')
        mb.boxc(0, 0, stand - 0.06, r * 2.1, r * 2.1, stand, 'M_MetalRust')
        z0 = stand
    if kind == 'plastic':
        prof = [(0, 0)]
        k = 5
        for i in range(k + 1):
            z = h * 0.85 * i / k
            prof.append((r * (1.0 if i % 2 == 0 else 1.03), z))
        prof += [(r * 0.92, h * 0.93), (r * 0.4, h), (r * 0.3, h * 1.02), (r * 0.3, h * 1.08), (0, h * 1.08)]
        mb.revolve([(a, b) for a, b in prof], 20, 'M_WindowDark', center=(0, 0, z0))
    else:  # concrete / brick box tank
        mb.boxc(0, 0, z0, r * 2.2, r * 2.2, z0 + h, 'M_Concrete')
        mb.boxc(0, 0, z0 + h, r * 0.6, r * 0.6, z0 + h + 0.08, 'M_MetalRust')
    # pipe down
    mb.cylinder(r * 0.8, 0, 0, z0 + 0.2, 0.025, 6, 'M_MetalRust', caps=False)
    return mb


def antenna(h=2.5):
    mb = MB()
    mb.cylinder(0, 0, 0, h, 0.02, 6, 'M_Steel')
    for k, z in enumerate((h - 0.1, h - 0.4, h - 0.7)):
        L = 0.9 - k * 0.2
        mb.beam((-L / 2, 0, z), (L / 2, 0, z), 0.015, 0.015, 'M_Steel')
    return mb


def rebar_stubs(mb, x, y, z, n=4, h=0.8):
    for i in range(n):
        dx = (i % 2) * 0.12 - 0.06
        dy = (i // 2) * 0.12 - 0.06
        mb.box(x + dx - 0.008, y + dy - 0.008, z, x + dx + 0.008, y + dy + 0.008, z + h, 'M_Steel')


def wire_hook(mb, x, z, y0=0.0):
    """L-shaped electric wire hook with insulator on a -Y facing wall."""
    mb.box(x - 0.012, y0 - 0.3, z - 0.012, x + 0.012, y0, z + 0.012, 'M_MetalRust')
    mb.box(x - 0.012, y0 - 0.3, z, x + 0.012, y0 - 0.276, z + 0.14, 'M_MetalRust')
    mb.cylinder(x, y0 - 0.288, z + 0.14, z + 0.22, 0.035, 8, 'M_Whitewash')


def rolling_shutter(mb, x0, x1, z_bot, z_top, y=0.1, mat='M_Shutter', housing=True, y_house=0.0):
    """Corrugated rolling shutter panel spanning x0..x1 from z_bot to z_top at depth y (facing -Y)."""
    if z_top - z_bot > 0.05:
        pitch = 0.075
        n = max(1, int((z_top - z_bot) / pitch))
        prof = []
        for i in range(n):
            za = z_bot + i * pitch
            prof += [(0.0, za), (0.012, za + pitch * 0.25), (0.012, za + pitch * 0.75)]
        prof.append((0.0, z_top))
        mb.sweep_path([(x0, y), (x1, y)], prof, mat, closed=False, caps=False)
        # bottom bar
        mb.box(x0, y - 0.03, z_bot, x1, y + 0.01, z_bot + 0.05, 'M_MetalRust')
    if housing:
        mb.box(x0 - 0.05, y_house - 0.22, z_top, x1 + 0.05, y_house, z_top + 0.32, mat, skip=('+y',))


def awning_corrugated(mb, x0, x1, z, dp=1.2, drop=0.35, mat='M_CorrugatedRust', y0=0.0):
    nx = max(4, int((x1 - x0) / 0.06))
    top, bot = [], []
    for i in range(nx + 1):
        x = lerp(x0, x1, i / nx)
        dz = 0.018 * math.sin(i * math.pi / 1.0)
        top.append(V(x, y0, z + dz))
        bot.append(V(x, y0 - dp, z - drop + dz))
    for i in range(nx):
        q = [top[i], top[i + 1], bot[i + 1], bot[i]]
        mb.face(q, mat, normal=(0, -0.3, 1))
        mb.face([p + Vector((0, 0, -0.01)) for p in q], mat, normal=(0, 0.3, -1))
    for x in (x0 + 0.15, x1 - 0.15):
        mb.beam((x, y0, z - 0.75), (x, y0 - dp * 0.85, z - drop * 0.85 - 0.02), 0.03, 0.03, 'M_MetalRust')


def awning_cloth(mb, x0, x1, z, dp=1.1, drop=0.45, mat='M_Cloth', y0=0.0):
    nx, ny = max(6, int((x1 - x0) / 0.25)), 4
    grid = []
    for i in range(nx + 1):
        s = i / nx
        row = []
        for j in range(ny + 1):
            t = j / ny
            sag = 0.08 * math.sin(math.pi * t) * (0.6 + 0.4 * math.sin(math.pi * s))
            row.append(V(lerp(x0, x1, s), y0 - dp * t, z - drop * t - sag))
        grid.append(row)
    for i in range(nx):
        for j in range(ny):
            q = [grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]]
            mb.face(q, mat, normal=(0, -0.3, 1))
            mb.face([p + Vector((0, 0, -0.008)) for p in q], mat, normal=(0, 0.3, -1))
    # scalloped valance
    for i in range(nx):
        a = grid[i][ny]
        b = grid[i + 1][ny]
        m = (a + b) / 2 + Vector((0, 0, -0.18))
        mb.face([a, b, m], mat, normal=(0, -1, 0))
        mb.face([a + Vector((0, 0.005, 0)), b + Vector((0, 0.005, 0)), m + Vector((0, 0.005, 0))], mat, normal=(0, 1, 0))
    for x in (x0 + 0.05, x1 - 0.05):
        mb.beam((x, y0, z), (x, y0 - dp, z - drop), 0.02, 0.02, 'M_WoodPlanks')
        mb.cylinder(x, y0 - dp, z - drop - 2.2, z - drop, 0.025, 6, 'M_WoodPlanks', caps=False)


def signboard(mb, x0, x1, z0, z1, y=-0.12, frame_mat='M_MetalRust'):
    """Plain signboard quad (M_Signboard, 0..1 UVs) with a thin frame."""
    t = 0.05
    mb.box(x0 - 0.04, y, z0 - 0.04, x1 + 0.04, y + t, z1 + 0.04, frame_mat, skip=('-y',))
    # frame lips around the front
    mb.box(x0 - 0.04, y - 0.02, z0 - 0.04, x1 + 0.04, y, z0, frame_mat)
    mb.box(x0 - 0.04, y - 0.02, z1, x1 + 0.04, y, z1 + 0.04, frame_mat)
    mb.box(x0 - 0.04, y - 0.02, z0, x0, y, z1, frame_mat)
    mb.box(x1, y - 0.02, z0, x1 + 0.04, y, z1, frame_mat)
    o = V(x0, y - 0.005, z0)
    mb.face([V(x0, y - 0.005, z0), V(x1, y - 0.005, z0), V(x1, y - 0.005, z1), V(x0, y - 0.005, z1)], 'M_Signboard',
            normal=(0, -1, 0), uvo=(o, Vector((1, 0, 0)), Vector((0, 0, 1)), x1 - x0, z1 - z0))
    # hanging brackets to wall
    for x in (x0 + 0.1, x1 - 0.1):
        mb.box(x - 0.015, y + t, z1 - 0.1, x + 0.015, 0.0, z1 - 0.07, frame_mat)
