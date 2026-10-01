"""
kit_buildings.py - parametric building blocks: generic multi-storey block with facades, riverfront houses,
palaces, town shop-houses. All seeded / deterministic.
"""
import math
import random
from mathutils import Vector
from kit_core import MB, V, T, Rz, S, lerp, regular_poly
from kit_arch import (facade_wall, fits, jharokha, balcony, chhajja_x, chhatri, dome, water_tank, antenna,
                      rebar_stubs, wire_hook, rolling_shutter, awning_corrugated, awning_cloth, signboard,
                      flag_pole, shikhara, kalash, arch_panel, corbels, PROF_BAND, PROF_CORNICE, PROF_PLINTH,
                      PROF_BAND_SMALL, scaled_profile, pyramid_roof)

FH = 3.2
DROPPED = []   # openings rejected by fits() - reported by build_kit.py


def keep_fitting(ops, u0, u1, z0, z1):
    out = []
    for o in ops:
        if fits(o, u0, u1, z0, z1):
            out.append(o)
        else:
            DROPPED.append(o)
    return out


def sides_frames(x0, x1, y0, y1):
    return {
        'front': (T(0, y0, 0), x0, x1),
        'back': (T(0, y1, 0) @ Rz(180), -x1, -x0),
        'left': (T(x0, 0, 0) @ Rz(-90), -y1, -y0),
        'right': (T(x1, 0, 0) @ Rz(90), y0, y1),
    }


def subtract_intervals(a, b, cuts):
    segs = [(a, b)]
    for (c0, c1) in cuts:
        out = []
        for (s0, s1) in segs:
            if c1 <= s0 or c0 >= s1:
                out.append((s0, s1))
                continue
            if c0 > s0:
                out.append((s0, c0))
            if c1 < s1:
                out.append((c1, s1))
        segs = out
    return [(s0, s1) for (s0, s1) in segs if s1 - s0 > 0.05]


# ======================================================================= parapets
def parapet(mb, x0, y0, x1, y1, z, style, mat, coping_mat, h=1.0, t=0.22, clip=(), rng=None, sides='all'):
    """Parapet around rectangle top at z. clip = rects (x0,y0,x1,y1) where parapet is omitted."""
    rng = rng or random.Random(0)
    tol = 0.05
    edges = []
    # (axis, fixed coord range, interval a..b)
    if 'front' in sides or sides == 'all':
        edges.append(('x', y0, y0 + t, x0, x1))
    if 'back' in sides or sides == 'all':
        edges.append(('x', y1 - t, y1, x0, x1))
    if 'left' in sides or sides == 'all':
        edges.append(('y', x0, x0 + t, y0 + t, y1 - t))
    if 'right' in sides or sides == 'all':
        edges.append(('y', x1 - t, x1, y0 + t, y1 - t))
    for (ax, c0, c1, a, b) in edges:
        cuts = []
        for (rx0, ry0, rx1, ry1) in clip:
            if ax == 'x':
                if ry0 - tol <= c1 and ry1 + tol >= c0:
                    cuts.append((rx0 - 0.01, rx1 + 0.01))
            else:
                if rx0 - tol <= c1 and rx1 + tol >= c0:
                    cuts.append((ry0 - 0.01, ry1 + 0.01))
        for (s0, s1) in subtract_intervals(a, b, cuts):
            if ax == 'x':
                box = lambda za, zb, e=0.0, m=mat: mb.box(s0 - (e if s0 <= x0 + 1e-3 else 0), c0 - e, za,
                                                          s1 + (e if s1 >= x1 - 1e-3 else 0), c1 + e, zb, m, skip=('-z',))
                L = s1 - s0
            else:
                box = lambda za, zb, e=0.0, m=mat: mb.box(c0 - e, s0, za, c1 + e, s1, zb, m, skip=('-z',))
                L = s1 - s0
            if style == 'balustrade':
                box(z, z + 0.18, 0.02)
                box(z + h - 0.1, z + h, 0.03, coping_mat)
                n = max(1, int(L / 0.2))
                for i in range(n):
                    p = s0 + (i + 0.5) * L / n
                    cc = (c0 + c1) / 2
                    if ax == 'x':
                        mb.cylinder(p, cc, z + 0.18, z + h - 0.1, 0.045, 6, mat, caps=False)
                    else:
                        mb.cylinder(cc, p, z + 0.18, z + h - 0.1, 0.045, 6, mat, caps=False)
                # piers
                for p in (s0, s1):
                    cc = (c0 + c1) / 2
                    if ax == 'x':
                        mb.boxc(min(max(p, s0 + 0.12), s1 - 0.12), cc, z, 0.24, t + 0.04, z + h + 0.05, mat)
                    else:
                        mb.boxc(cc, min(max(p, s0 + 0.12), s1 - 0.12), z, t + 0.04, 0.24, z + h + 0.05, mat)
            elif style == 'merlon':
                box(z, z + h * 0.55)
                box(z + h * 0.55, z + h * 0.62, 0.03, coping_mat)
                n = max(1, int(L / 0.75))
                for i in range(n):
                    p = s0 + (i + 0.5) * L / n
                    cc = (c0 + c1) / 2
                    if ax == 'x':
                        mb.boxc(p, cc, z + h * 0.62, 0.34, t, z + h * 1.02, mat)
                        mb.add(pyramid_roof(0.34, t, 0.16, mat, overhang=0.0), T(p, cc, z + h * 1.02))
                    else:
                        mb.boxc(cc, p, z + h * 0.62, t, 0.34, z + h * 1.02, mat)
                        mb.add(pyramid_roof(t, 0.34, 0.16, mat, overhang=0.0), T(cc, p, z + h * 1.02))
            else:
                box(z, z + h)
                box(z + h, z + h + 0.07, 0.035, coping_mat)
                if style == 'pinnacle':
                    n = max(1, int(L / 2.2))
                    for i in range(n + 1):
                        p = s0 + i * L / n
                        p = min(max(p, s0 + 0.12), s1 - 0.12)
                        cc = (c0 + c1) / 2
                        if ax == 'x':
                            mb.boxc(p, cc, z + h + 0.07, 0.24, 0.24, z + h + 0.4, coping_mat)
                            mb.add(kalash(0.45, coping_mat, seg=8), T(p, cc, z + h + 0.4))
                        else:
                            mb.boxc(cc, p, z + h + 0.07, 0.24, 0.24, z + h + 0.4, coping_mat)
                            mb.add(kalash(0.45, coping_mat, seg=8), T(cc, p, z + h + 0.4))


# ======================================================================= generic block
def _win_op(rng, st, cx, zf, bw, kind=None, trim='M_PlasterWhite'):
    kind = kind or rng.choice(st.get('win_kinds', ['rect', 'arch', 'cusped']))
    w = max(0.75, min(1.35, bw * rng.uniform(0.36, 0.46)))
    h = rng.uniform(1.55, 1.8) if kind == 'rect' else rng.uniform(1.85, 2.1)
    fills = st.get('fills', ['bars', 'shutters', 'none', 'half_shutter', 'glass_grid'])
    fill = rng.choice(fills)
    if kind != 'rect' and fill == 'shutters':
        fill = 'bars'
    return dict(kind=kind, cx=cx, sill=zf + 0.85, w=w, h=h, depth=rng.uniform(0.22, 0.34), fw=st.get('fw', 0.11),
                fd=0.045, frame_mat=trim, fill=fill, ledge=(kind == 'rect'),
                hood=(rng.random() < st.get('hood_p', 0.35) * (1.0 if kind == 'rect' else 0.5)),
                hood_mat=trim)


def make_block(mb, b, rng):
    """Build a multi-storey block. See module docs for keys. Returns info dict."""
    x0, x1, y0, y1, z0 = b['x0'], b['x1'], b['y0'], b['y1'], b['z0']
    floors = b['floors']
    hs = [b.get('fh0', FH)] + [b.get('fh', FH)] * (floors - 1)
    zf = [z0]
    for h in hs:
        zf.append(zf[-1] + h)
    ztop = zf[-1]
    mat = b['mat']
    trim = b.get('trim', 'M_PlasterWhite')
    st = b.get('style', {})
    sides = b.get('sides', {'front': 'rich', 'left': 'plain', 'right': 'plain', 'back': 'plain'})
    frames = sides_frames(x0, x1, y0, y1)
    floor_mats = b.get('floor_mats', {})
    occl = b.get('occl', [])  # (u0, u1, f0, f1) on the front facade to leave blank
    custom = b.get('custom', {})
    info = dict(ztop=ztop, zf=zf, bays={})

    for side, (M, u0, u1) in frames.items():
        kind = sides.get(side, 'none')
        if kind is None:
            continue
        width = u1 - u0
        sub = MB()
        if kind == 'rich':
            bay_w = st.get('bay', 3.0)
            nb = max(1, int(round(width / bay_w)))
            bw = width / nb
            centers = [u0 + (i + 0.5) * bw for i in range(nb)]
            info['bays'][side] = centers
            row_kinds = {}
            for f in range(floors):
                row_kinds[f] = st.get('row_kinds', {}).get(f) or rng.choice(st.get('win_kinds', ['rect', 'arch', 'cusped']))
            jhar = set(tuple(j) for j in st.get('jharokhas', []))
            balc_floors = set(st.get('balc_floors', []))
            for f in range(floors):
                zz = zf[f]
                hf = hs[f]
                fmat = floor_mats.get(f, mat)
                ops = []
                if (side, f) in custom:
                    ops = custom[(side, f)](sub, u0, u1, zz, hf, rng, centers, bw) or []
                else:
                    runs = []
                    cur = []
                    for i, cx in enumerate(centers):
                        blocked = any(o[0] - 0.2 <= cx <= o[1] + 0.2 and o[2] <= f <= o[3] for o in occl)
                        if blocked:
                            if cur:
                                runs.append(cur)
                                cur = []
                            continue
                        if f == 0 and b.get('ground', True):
                            gs = st.get('ground', 'doors')
                            if gs == 'arcade':
                                ops.append(dict(kind=st.get('arcade_kind', 'cusped'), cx=cx, sill=zz + 0.22, w=bw * 0.7,
                                                h=hf - 0.62, depth=1.6, fw=0.14, fd=0.06, frame_mat=trim, back_mat=fmat,
                                                reveal_mat=fmat))
                                # dark doorway at the back of the loggia
                                ops[-1]['back_mat'] = 'M_WindowDark' if rng.random() < 0.5 else 'M_WoodShutter'
                            elif i in st.get('doors', [nb // 2]):
                                ops.append(dict(kind=st.get('door_kind', 'arch'), cx=cx, sill=zz + 0.24, w=min(1.4, bw - 0.6),
                                                h=min(2.5, hf - 0.62), depth=0.4, fw=0.16, fd=0.06, frame_mat=st.get('door_frame', trim),
                                                back_mat='M_WoodShutter'))
                            else:
                                ops.append(dict(kind='rect', cx=cx, sill=zz + 1.05, w=min(0.9, bw * 0.35), h=1.15, depth=0.25,
                                                fw=0.08, frame_mat=trim, fill='bars', ledge=True))
                            continue
                        if (f, i) in jhar:
                            if cur:
                                runs.append(cur)
                                cur = []
                            jw = min(bw - 0.35, st.get('jhar_w', 2.2))
                            jh = jharokha(w=jw, h=min(2.3, hf - 0.8), dp=st.get('jhar_dp', 0.85), n_arches=3 if jw > 1.7 else 2,
                                          roof=st.get('jhar_roof', 'bangla'), body_mat=st.get('jhar_mat', trim),
                                          trim_mat=st.get('jhar_trim', trim), roof_mat=st.get('jhar_roof_mat'),
                                          arch_kind=st.get('jhar_arch', 'cusped'), seed=rng.randint(0, 999))
                            sub.add(jh, T(cx, 0, zz + 0.55))
                            continue
                        if f in balc_floors:
                            ops.append(dict(kind=st.get('balc_door_kind', row_kinds[f] if row_kinds[f] != 'cusped' else 'arch'),
                                            cx=cx, sill=zz + 0.15, w=min(1.2, bw * 0.42), h=2.35, depth=0.35, fw=0.1, fd=0.045,
                                            frame_mat=trim, back_mat=rng.choice(['M_WindowDark', 'M_WindowDark', 'M_WoodShutter'])))
                            cur.append(cx)
                            continue
                        if cur:
                            runs.append(cur)
                            cur = []
                        if rng.random() < st.get('blank_p', 0.07):
                            continue
                        if bw > 3.4 and rng.random() < st.get('pair_p', 0.35):
                            k = row_kinds[f]
                            for dx in (-bw * 0.2, bw * 0.2):
                                op = _win_op(rng, st, cx + dx, zz, bw * 0.55, k, trim)
                                ops.append(op)
                        else:
                            ops.append(_win_op(rng, st, cx, zz, bw, row_kinds[f], trim))
                    if cur:
                        runs.append(cur)
                    for run in runs:
                        a = run[0] - bw / 2 + 0.15
                        c = run[-1] + bw / 2 - 0.15
                        a = max(a, u0 + 0.1)
                        c = min(c, u1 - 0.1)
                        bl = balcony(w=c - a, dp=st.get('balc_dp', 1.0), style=st.get('balc_style', 'balusters'),
                                     slab_mat=st.get('balc_mat', trim), rail_mat=st.get('balc_rail_mat', trim),
                                     cloth=('M_Cloth' if rng.random() < st.get('cloth_p', 0.4) else None), seed=rng.randint(0, 99))
                        sub.add(bl, T((a + c) / 2, 0, zz))
                    if f in st.get('chhajja_floors', []) and f not in balc_floors:
                        chhajja_x(sub, u0 + 0.1, u1 - 0.1, zz + 3.0 if hf > 3.0 else zz + hf - 0.2, trim, dp=0.55)
                ops = keep_fitting(ops, u0, u1, zz, zz + hf)
                facade_wall(sub, u0, u1, zz, zz + hf, ops, fmat)
        elif kind == 'plain':
            nb = max(1, int(width / st.get('side_bay', 3.2)))
            bw = width / nb
            for f in range(floors):
                zz = zf[f]
                hf = hs[f]
                fmat = floor_mats.get(f, mat)
                ops = []
                if (side, f) in custom:
                    ops = custom[(side, f)](sub, u0, u1, zz, hf, rng, None, bw) or []
                else:
                    for i in range(nb):
                        if rng.random() < st.get('side_p', 0.5):
                            ww = min(0.75, bw - 0.4)
                            if ww < 0.3:
                                continue
                            jit = max(0.0, min(0.3, (bw - ww) / 2 - 0.2))
                            cx = u0 + (i + 0.5) * bw + rng.uniform(-jit, jit)
                            k = rng.choice(['rect', 'rect', 'arch'])
                            ops.append(dict(kind=k, cx=cx, sill=zz + 1.0, w=ww, h=1.25 if k == 'rect' else 1.5,
                                            depth=0.22, fw=0.07 if rng.random() < 0.6 else 0.0, frame_mat=trim,
                                            fill=rng.choice(['bars', 'none', 'half_shutter'])))
                ops = keep_fitting(ops, u0, u1, zz, zz + hf)
                facade_wall(sub, u0, u1, zz, zz + hf, ops, fmat)
        else:  # blank wall
            for f in range(floors):
                zz = zf[f]
                facade_wall(sub, u0, u1, zz, zz + hs[f], [], floor_mats.get(f, mat))
        mb.add(sub, M)

    if b.get('bands', True):
        bp = b.get('band_p', 1.0)
        for f in range(1, floors):
            differs = floor_mats.get(f, mat) != floor_mats.get(f - 1, mat)
            if differs or rng.random() < bp:
                mb.ring_rect(x0, y0, x1, y1, b.get('band_prof', PROF_BAND), trim, z0=zf[f])
            else:
                mb.ring_rect(x0, y0, x1, y1, PROF_BAND_SMALL, trim, z0=zf[f])
    if b.get('base_band'):
        mb.ring_rect(x0, y0, x1, y1, PROF_PLINTH, b.get('base_mat', trim), z0=z0)
    if b.get('cornice', True):
        mb.ring_rect(x0, y0, x1, y1, b.get('cornice_prof', PROF_CORNICE), b.get('cornice_mat', trim), z0=ztop)
    if b.get('roof', True):
        mb.face([V(x0, y0, ztop), V(x1, y0, ztop), V(x1, y1, ztop), V(x0, y1, ztop)], b.get('roof_mat', 'M_Concrete'),
                normal=(0, 0, 1))
    if b.get('bottom'):
        mb.face([V(x0, y0, z0), V(x1, y0, z0), V(x1, y1, z0), V(x0, y1, z0)], mat, normal=(0, 0, -1))
    ps = b.get('parapet', 'plain')
    if ps:
        parapet(mb, x0, y0, x1, y1, ztop + (0.08 if b.get('cornice', True) else 0.0), ps, b.get('parapet_mat', mat),
                b.get('coping_mat', trim), h=b.get('parapet_h', 1.0), clip=b.get('clip', []), rng=rng,
                sides=b.get('parapet_sides', 'all'))
    return info


# ======================================================================= roof clutter
def mumty(mb, x, y, z, rng, mat, trim, w=2.8, d=3.0, door_side='front'):
    """Stair-head room on a roof, centred at x,y, base z."""
    b = dict(x0=x - w / 2, x1=x + w / 2, y0=y - d / 2, y1=y + d / 2, z0=z, floors=1, fh0=2.6, mat=mat, trim=trim,
             sides={'front': 'none', 'left': 'none', 'right': 'none', 'back': 'none'}, parapet=None, bands=False,
             cornice_prof=scaled_profile(PROF_BAND_SMALL, 1.5, 1.5), ground=False)

    def door(sub, u0, u1, zz, hf, rng_, c, bw):
        return [dict(kind='rect', cx=(u0 + u1) / 2 + 0.3, sill=zz + 0.12, w=0.9, h=2.05, depth=0.12, fw=0.0,
                     back_mat='M_WoodShutter' if rng_.random() < 0.6 else 'M_MetalRust')]
    b['sides'][door_side] = 'plain'
    b['custom'] = {(door_side, 0): door}
    make_block(mb, b, rng)
    return z + 2.6


def roof_clutter(mb, rng, x0, y0, x1, y1, z, mat, trim, opts):
    """Scatter rooftop items inside rectangle at height z."""
    W = x1 - x0
    D = y1 - y0
    placed = []

    def free(px, py, r):
        for (qx, qy, qr) in placed:
            if math.hypot(px - qx, py - qy) < r + qr:
                return False
        return True
    if opts.get('mumty', True) and W > 4 and D > 4:
        mx = x1 - 1.8 if rng.random() < 0.5 else x0 + 1.8
        my = y1 - 1.9
        top = mumty(mb, mx, my, z, rng, opts.get('mumty_mat', mat), trim)
        placed.append((mx, my, 2.2))
        # tank on the mumty
        if rng.random() < 0.8:
            mb.add(water_tank('plastic', r=rng.uniform(0.45, 0.6), h=rng.uniform(0.9, 1.2)), T(mx, my + 0.3, top + 0.08))
    for i in range(opts.get('tanks', rng.randint(1, 3))):
        for _ in range(20):
            px = rng.uniform(x0 + 1.0, x1 - 1.0)
            py = rng.uniform(y0 + D * 0.45, y1 - 1.0)
            if free(px, py, 0.9):
                placed.append((px, py, 0.8))
                kind = 'plastic' if rng.random() < 0.7 else 'concrete'
                mb.add(water_tank(kind, r=rng.uniform(0.45, 0.65), h=rng.uniform(0.9, 1.3), stand=rng.choice([0.0, 0.0, 0.8, 1.2])),
                       T(px, py, z))
                break
    if opts.get('antenna', rng.random() < 0.5):
        px, py = rng.uniform(x0 + 0.6, x1 - 0.6), rng.uniform(y0 + D * 0.5, y1 - 0.6)
        mb.add(antenna(rng.uniform(2.0, 3.2)), T(px, py, z))
    if opts.get('flag', rng.random() < 0.5):
        px, py = x0 + 0.4 if rng.random() < 0.5 else x1 - 0.4, y0 + 0.4
        mb.add(flag_pole(rng.uniform(3.5, 5.5), seed=rng.randint(0, 50)), T(px, py, z))
    if opts.get('rebar', False):
        for (px, py) in ((x0 + 0.3, y0 + 0.3), (x1 - 0.3, y0 + 0.3), (x0 + 0.3, y1 - 0.3), (x1 - 0.3, y1 - 0.3)):
            mb.boxc(px, py, z, 0.3, 0.3, z + 0.35, 'M_Concrete')
            rebar_stubs(mb, px, py, z + 0.35, 4, rng.uniform(0.5, 1.0))
    if opts.get('shrine', False):
        from kit_arch import shikhara as _sh
        px = (x0 + x1) / 2 + rng.uniform(-W * 0.2, W * 0.2)
        py = y0 + D * 0.35
        if free(px, py, 1.3):
            placed.append((px, py, 1.3))
            mb.boxc(px, py, z, 1.9, 1.9, z + 0.35, 'M_Sandstone')
            mb.boxc(px, py, z + 0.35, 1.4, 1.4, z + 1.9, 'M_Whitewash')
            mb.add(_sh(0.75, 2.2, 'M_Whitewash', top_mat='M_Saffron', seg=40, urus=False, seed=rng.randint(0, 9)),
                   T(px, py, z + 1.9))
    if opts.get('clothesline', rng.random() < 0.5) and W > 5:
        py = rng.uniform(y0 + 1.5, y1 - 1.5)
        a, c = x0 + 0.5, x1 - 0.5
        for px in (a, c):
            mb.box(px - 0.02, py - 0.02, z, px + 0.02, py + 0.02, z + 1.9, 'M_MetalRust')
        mb.beam((a, py, z + 1.85), (c, py, z + 1.85), 0.01, 0.01, 'M_Steel')
        n = rng.randint(2, 4)
        for i in range(n):
            cx = lerp(a + 0.6, c - 0.6, (i + 0.5) / n)
            cw = rng.uniform(0.5, 1.1)
            ch = rng.uniform(0.5, 1.0)
            q = [V(cx - cw / 2, py, z + 1.84), V(cx + cw / 2, py, z + 1.84), V(cx + cw / 2, py, z + 1.84 - ch), V(cx - cw / 2, py, z + 1.84 - ch)]
            mb.face(q, 'M_Cloth', normal=(0, -1, 0))
            mb.face([p + Vector((0, 0.006, 0)) for p in q], 'M_Cloth', normal=(0, 1, 0))


# ======================================================================= riverfront houses
PLASTERS = ['M_PlasterYellow', 'M_PlasterOchre', 'M_PlasterRed', 'M_PlasterBlue', 'M_PlasterWhite',
            'M_PlasterPainted', 'M_PlasterPeeling', 'M_PlasterWorn', 'M_PlasterMossy', 'M_PlasterDamaged',
            'M_BrickPlaster']


def riverfront_house(seed, W, D, floors, p):
    """p: dict of design knobs (see RIVERFRONT_VARIANTS)."""
    rng = random.Random(seed)
    mb = MB()
    x0, x1 = -W / 2, W / 2
    y0, y1 = 0.0, D
    hp = p.get('plinth_h', 1.6)
    trim = p.get('trim', 'M_PlasterWhite')
    mat = p['mat']
    # ---- sandstone plinth (ghat level) with niches / doorway
    py0 = -0.45
    pm = p.get('plinth_mat', 'M_SandstoneRed')
    sub = MB()
    ops = []
    if hp > 1.2:
        n = max(1, int(W / 4.0))
        for i in range(n):
            cx = x0 + (i + 0.5) * W / n
            if rng.random() < 0.55:
                ops.append(dict(kind='arch', cx=cx, sill=0.15, w=0.7, h=min(hp - 0.45, 1.5), depth=0.5, fw=0.08, fd=0.03,
                                frame_mat='M_Sandstone', back_mat='M_WindowDark'))
    ops = keep_fitting(ops, x0 - 0.3, x1 + 0.3, 0.0, hp)
    facade_wall(sub, x0 - 0.3, x1 + 0.3, 0.0, hp, ops, pm)
    mb.add(sub, T(0, py0, 0))
    mb.box(x0 - 0.3, py0, 0, x1 + 0.3, y1 + 0.2, hp, pm, skip=('-y', '-z'))
    mb.sweep_x(x0 - 0.3, x1 + 0.3, py0, [(0, 0), (0.12, 0.0), (0.12, 0.3), (0, 0.36)], pm)
    mb.sweep_x(x0 - 0.3, x1 + 0.3, py0, [(0, -0.12), (0.06, -0.12), (0.06, 0.0), (0, 0.0)], 'M_Sandstone', z0=hp)
    # ---- main block
    style = dict(p.get('style', {}))
    blocks = []
    main = dict(x0=x0, x1=x1, y0=y0, y1=y1, z0=hp, floors=floors, mat=mat, trim=trim, style=style,
                floor_mats=p.get('floor_mats', {}), parapet=p.get('parapet', 'plain'), parapet_h=p.get('parapet_h', 1.0),
                sides=p.get('sides', {'front': 'rich', 'left': 'plain', 'right': 'plain', 'back': 'plain'}),
                cornice_mat=p.get('cornice_mat', trim), coping_mat=p.get('coping_mat', trim), clip=[],
                band_p=p.get('band_p', 0.55))
    zt = hp + floors * FH
    ptop = zt + 0.08
    upper = []
    # setback terrace storey(s)
    if p.get('setback'):
        sb = p['setback']
        ux0 = x0 + sb.get('left', 0.0)
        ux1 = x1 - sb.get('right', 0.0)
        uy0 = y0 + sb.get('front', 2.5)
        u = dict(x0=ux0, x1=ux1, y0=uy0, y1=y1, z0=ptop, floors=sb.get('floors', 1), mat=sb.get('mat', mat), trim=trim,
                 style=dict(style, balc_floors=[], jharokhas=[], chhajja_floors=[0] if sb.get('chhajja') else []),
                 parapet=sb.get('parapet', 'plain'), ground=False, cornice_mat=p.get('cornice_mat', trim),
                 sides={'front': 'rich', 'left': 'plain', 'right': 'plain', 'back': 'plain'}, clip=[])
        upper.append(u)
    if p.get('tower'):
        tw = p['tower']
        side = tw.get('side', 'right')
        w = tw.get('w', 4.0)
        tx0, tx1 = (x1 - w, x1) if side == 'right' else (x0, x0 + w)
        u = dict(x0=tx0, x1=tx1, y0=y0 + tw.get('front', 0.0), y1=y0 + tw.get('depth', D * 0.6), z0=ptop, floors=tw.get('floors', 1),
                 mat=tw.get('mat', mat), trim=trim, style=dict(style, balc_floors=[], jharokhas=[], bay=w / 1.0, row_kinds={0: 'cusped', 1: 'arch'}),
                 parapet=tw.get('parapet', 'merlon'), ground=False, cornice_mat=p.get('cornice_mat', trim),
                 sides={'front': 'rich', 'left': 'plain', 'right': 'plain', 'back': 'plain'}, clip=[])
        upper.append(u)
    main['clip'] = [(u['x0'], u['y0'], u['x1'], u['y1']) for u in upper]
    # projecting bay (oriel column)
    occl = []
    bay = p.get('bay')
    if bay:
        bx = bay.get('x', 0.0)
        bwid = bay.get('w', 3.0)
        f0, f1 = bay.get('f0', 1), bay.get('f1', floors - 1)
        occl.append((bx - bwid / 2, bx + bwid / 2, f0, f1))
    main['occl'] = occl
    info = make_block(mb, main, rng)
    for u in upper:
        make_block(mb, u, rng)
    if bay:
        bdp = bay.get('dp', 0.8)
        bz0 = hp + FH * f0 - 0.1
        bb = dict(x0=bx - bwid / 2, x1=bx + bwid / 2, y0=-bdp, y1=0.0, z0=bz0, floors=f1 - f0 + 1, fh0=FH + 0.1,
                  mat=bay.get('mat', trim if bay.get('stone') else mat), trim=bay.get('trim', trim),
                  style=dict(style, bay=bwid, balc_floors=[], jharokhas=[], chhajja_floors=[], row_kinds={i: bay.get('kind', 'cusped') for i in range(10)},
                             pair_p=0.0, side_p=1.0, side_bay=bdp),
                  sides={'front': 'rich', 'left': 'plain', 'right': 'plain', 'back': None}, ground=False, bottom=True,
                  parapet=bay.get('parapet', 'balustrade'), parapet_h=0.8, parapet_sides=('front', 'left', 'right'),
                  cornice_prof=scaled_profile(PROF_CORNICE, 0.6, 0.6), roof=True)
        bi = make_block(mb, bb, rng)
        cb = MB()
        corbels(cb, [bx - bwid / 2 + 0.2, bx, bx + bwid / 2 - 0.2], bdp, 0.9, bay.get('trim', trim), w=0.18)
        mb.add(cb, T(0, 0, bz0))
        if bay.get('dome'):
            mb.add(dome(min(bwid, bdp) * 0.45, bay.get('dome_mat', trim), style='onion', seg=20, lobed=True), T(bx, -bdp / 2, bi['ztop'] + 0.08))
    # ---- roof features on the top-most roof(s)
    if upper:
        top = max(upper, key=lambda u: u['z0'] + u['floors'] * FH)
        tz = top['z0'] + top['floors'] * FH + 0.08
        roof_clutter(mb, rng, top['x0'] + 0.3, top['y0'] + 0.3, top['x1'] - 0.3, top['y1'] - 0.3, tz, mat, trim,
                     dict(p.get('roof_opts', {}), mumty=False))
        # terrace items on main roof in front of the setback
        if p.get('setback'):
            roof_clutter(mb, rng, x0 + 0.4, y0 + 0.4, x1 - 0.4, upper[0]['y0'] - 0.2, ptop, mat, trim,
                         dict(mumty=False, tanks=0, antenna=False, flag=False, clothesline=True, shrine=p.get('roof_opts', {}).get('shrine', False)))
    else:
        roof_clutter(mb, rng, x0 + 0.3, y0 + 0.3, x1 - 0.3, y1 - 0.3, ptop, mat, trim, p.get('roof_opts', {}))
    # corner chhatris on the front parapet
    if p.get('corner_chhatris'):
        cs = p.get('chhatri_size', 1.5)
        cm = p.get('chhatri_mat', trim)
        for cx in (x0 + cs / 2, x1 - cs / 2):
            mb.add(chhatri(size=cs, height=cs * 1.0, pillar_mat=cm, dome_mat=cm, plinth_h=0.2, seg=16),
                   T(cx, y0 + cs / 2, ptop + p.get('parapet_h', 1.0) * 0.0 + 0.0))
    if p.get('roof_dome'):
        rd = p['roof_dome']
        mb.add(dome(rd.get('r', 1.6), rd.get('mat', trim), style=rd.get('style', 'onion'), seg=28, lobed=True,
                    drum_h=rd.get('drum', 0.8), drum_mat=rd.get('drum_mat', mat)), T(rd.get('x', 0.0), rd.get('y', D * 0.4), ptop))
    # painted name board on the plinth (ghat / guest-house name) - M_Signboard, 0..1 UVs
    if p.get('sign_plinth') and hp > 1.3:
        sw = min(W * 0.45, 6.0)
        sx = p.get('sign_x', 0.0)
        signboard(mb, sx - sw / 2, sx + sw / 2, hp * 0.52, hp * 0.52 + 0.55, y=py0 - 0.07, frame_mat='M_Sandstone')
    if p.get('sign_side'):
        # big painted hotel sign on the upper side wall facing the ghat approach
        sz = hp + FH * (floors - 1) + 0.4
        sub = MB()
        signboard(sub, -2.2, 2.2, sz, sz + 1.6, y=-0.07, frame_mat='M_MetalRust')
        mb.add(sub, T(x0, D * 0.35, 0) @ Rz(-90))
    # wire hooks on the facade
    for i in range(p.get('hooks', 2)):
        wire_hook(mb, rng.uniform(x0 + 0.5, x1 - 0.5), hp + FH + rng.uniform(1.3, 1.6), 0.0)
    return mb


# Riverfront variants: (name, seed, W, D, floors, params)
def RIVERFRONT_VARIANTS():
    V_ = []
    V_.append(('Bldg_Riverfront_01', 101, 12.0, 12.0, 5, dict(
        sign_plinth=True, mat='M_PlasterYellow', trim='M_PlasterWhite', plinth_h=2.2, floor_mats={0: 'M_PlasterMossy'},
        style=dict(bay=3.0, win_kinds=['arch', 'rect'], balc_floors=[2], jharokhas=[(3, 1), (3, 2)], chhajja_floors=[1, 4],
                   doors=[1], jhar_mat='M_SandstoneRed', jhar_trim='M_Sandstone'),
        roof_opts=dict(tanks=2, flag=True), corner_chhatris=True, chhatri_size=1.4, hooks=2)))
    V_.append(('Bldg_Riverfront_02', 202, 9.0, 11.0, 6, dict(
        sign_side=True, mat='M_PlasterBlue', trim='M_PlasterWhite', plinth_h=1.4, floor_mats={0: 'M_PlasterDamaged', 5: 'M_BrickPlaster'},
        style=dict(bay=3.0, win_kinds=['rect'], balc_floors=[1, 3], chhajja_floors=[2, 4], doors=[1], balc_style='iron', cloth_p=0.7),
        parapet='plain', roof_opts=dict(tanks=3, rebar=True, antenna=True))))
    V_.append(('Bldg_Riverfront_03', 303, 16.0, 14.0, 4, dict(
        sign_plinth=True, mat='M_PlasterOchre', trim='M_Sandstone', plinth_h=2.6, plinth_mat='M_SandstoneRed',
        style=dict(bay=3.2, win_kinds=['cusped'], jharokhas=[(1, 1), (1, 3), (2, 1), (2, 3)], balc_floors=[3], ground='arcade',
                   jhar_mat='M_Sandstone', jhar_roof='dome'),
        parapet='merlon', setback=dict(front=3.0, floors=1, mat='M_PlasterYellow', left=2.0, right=2.0),
        corner_chhatris=True, chhatri_size=1.8, chhatri_mat='M_Sandstone', roof_opts=dict(flag=True))))
    V_.append(('Bldg_Riverfront_04', 404, 8.0, 10.0, 7, dict(
        mat='M_PlasterPainted', trim='M_PlasterWhite', plinth_h=1.2, floor_mats={0: 'M_PlasterPeeling', 1: 'M_PlasterPeeling'},
        style=dict(bay=2.6, win_kinds=['rect', 'arch'], balc_floors=[2, 4, 6], doors=[1], balc_style='iron', cloth_p=0.6),
        parapet='plain', roof_opts=dict(tanks=2, clothesline=True))))
    V_.append(('Bldg_Riverfront_05', 505, 14.0, 12.0, 5, dict(
        mat='M_PlasterWhite', trim='M_PlasterYellow', plinth_h=2.0, floor_mats={0: 'M_PlasterWorn'},
        style=dict(bay=3.4, win_kinds=['pointed', 'rect'], balc_floors=[2], chhajja_floors=[1, 3, 4], doors=[0, 3]),
        bay=dict(x=0.0, w=3.4, dp=0.9, f0=1, f1=4, kind='cusped', dome=True, parapet='balustrade', trim='M_PlasterYellow'),
        parapet='balustrade', roof_opts=dict(tanks=2, shrine=True))))
    V_.append(('Bldg_Riverfront_06', 606, 18.0, 15.0, 6, dict(
        sign_side=True, mat='M_PlasterRed', trim='M_PlasterWhite', plinth_h=2.4, floor_mats={0: 'M_PlasterDamaged'},
        style=dict(bay=3.0, win_kinds=['arch', 'cusped', 'rect'], balc_floors=[2, 4], jharokhas=[(3, 0), (3, 5), (5, 2), (5, 3)],
                   chhajja_floors=[1], doors=[2, 3], jhar_mat='M_PlasterWhite'),
        tower=dict(side='left', w=4.5, floors=2, depth=7.0), parapet='pinnacle',
        roof_opts=dict(tanks=3, flag=True))))
    V_.append(('Bldg_Riverfront_07', 707, 10.0, 12.0, 3, dict(
        mat='M_PlasterMossy', trim='M_PlasterWhite', plinth_h=3.0, floor_mats={2: 'M_PlasterYellow'},
        style=dict(bay=3.3, win_kinds=['arch'], balc_floors=[1], doors=[1], chhajja_floors=[2]),
        parapet='plain', roof_dome=dict(r=1.3, x=2.0, y=6.0, mat='M_PlasterWhite', drum=0.6),
        roof_opts=dict(tanks=1, flag=True, mumty=False))))
    V_.append(('Bldg_Riverfront_08', 808, 20.0, 16.0, 5, dict(
        sign_plinth=True, sign_x=-4.0, mat='M_PlasterYellow', trim='M_SandstoneRed', plinth_h=2.8, floor_mats={0: 'M_SandstoneRed'},
        style=dict(bay=3.3, win_kinds=['cusped', 'arch'], ground='arcade', arcade_kind='cusped', jharokhas=[(2, 1), (2, 4), (4, 1), (4, 4)],
                   balc_floors=[3], jhar_mat='M_SandstoneRed', jhar_trim='M_Sandstone', balc_mat='M_SandstoneRed',
                   balc_rail_mat='M_Sandstone'),
        parapet='merlon', parapet_mat='M_SandstoneRed', coping_mat='M_Sandstone', corner_chhatris=True, chhatri_size=2.0,
        chhatri_mat='M_SandstoneRed', tower=dict(side='right', w=5.0, floors=1, depth=8.0, mat='M_PlasterYellow'),
        roof_opts=dict(tanks=2, flag=True))))
    V_.append(('Bldg_Riverfront_09', 909, 11.0, 13.0, 6, dict(
        mat='M_PlasterPeeling', trim='M_PlasterBlue', plinth_h=1.6, floor_mats={4: 'M_PlasterBlue', 5: 'M_PlasterBlue'},
        style=dict(bay=2.8, win_kinds=['rect'], balc_floors=[3], chhajja_floors=[1, 2, 4], doors=[1], balc_style='solid', fills=['bars', 'shutters']),
        setback=dict(front=2.0, floors=1, mat='M_BrickPlaster'), parapet='plain',
        roof_opts=dict(tanks=2, rebar=True))))
    V_.append(('Bldg_Riverfront_10', 1010, 13.0, 11.0, 4, dict(
        sign_plinth=True, mat='M_PlasterOchre', trim='M_PlasterWhite', plinth_h=2.0, floor_mats={0: 'M_PlasterMossy'},
        style=dict(bay=3.2, win_kinds=['arch', 'cusped'], jharokhas=[(2, 0), (2, 3)], balc_floors=[1, 3], doors=[1, 2]),
        bay=dict(x=0.0, w=3.0, dp=0.8, f0=2, f1=3, kind='arch', stone=True, trim='M_Sandstone', parapet='merlon'),
        parapet='balustrade', corner_chhatris=True, chhatri_size=1.3, roof_opts=dict(tanks=2))))
    V_.append(('Bldg_Riverfront_11', 1111, 15.0, 14.0, 7, dict(
        sign_side=True, mat='M_PlasterWhite', trim='M_PlasterOchre', plinth_h=2.2, floor_mats={0: 'M_PlasterDamaged', 1: 'M_PlasterWorn'},
        style=dict(bay=3.0, win_kinds=['rect', 'arch'], balc_floors=[2, 5], jharokhas=[(4, 2)], chhajja_floors=[3, 6], doors=[2],
                   jhar_mat='M_PlasterOchre'),
        tower=dict(side='right', w=4.0, floors=1, depth=6.0, mat='M_PlasterYellow', parapet='pinnacle'),
        parapet='plain', roof_opts=dict(tanks=3, antenna=True, flag=True))))
    V_.append(('Bldg_Riverfront_12', 1212, 9.5, 12.0, 4, dict(
        mat='M_BrickPlaster', trim='M_PlasterWhite', plinth_h=1.8, floor_mats={0: 'M_PlasterWorn', 1: 'M_PlasterWorn'},
        style=dict(bay=3.1, win_kinds=['rect'], balc_floors=[2], doors=[1], balc_style='iron', cloth_p=0.9, fills=['bars', 'half_shutter']),
        parapet='plain', roof_opts=dict(tanks=2, rebar=True, clothesline=True))))
    V_.append(('Bldg_Riverfront_13', 1313, 17.0, 13.0, 5, dict(
        sign_plinth=True, mat='M_PlasterBlue', trim='M_PlasterWhite', plinth_h=2.5, floor_mats={0: 'M_PlasterMossy'},
        style=dict(bay=3.4, win_kinds=['cusped', 'pointed'], jharokhas=[(2, 2), (4, 2)], balc_floors=[1, 3], doors=[1, 3],
                   jhar_mat='M_PlasterWhite', jhar_roof='dome', chhajja_floors=[4]),
        parapet='merlon', corner_chhatris=True, chhatri_size=1.6, roof_opts=dict(shrine=True, tanks=1))))
    V_.append(('Bldg_Riverfront_14', 1414, 12.5, 12.0, 6, dict(
        mat='M_PlasterYellow', trim='M_PlasterRed', plinth_h=1.5, floor_mats={0: 'M_PlasterDamaged', 5: 'M_PlasterPainted'},
        style=dict(bay=3.1, win_kinds=['rect', 'arch'], balc_floors=[1, 3, 5], doors=[1], balc_style='balusters', chhajja_floors=[2, 4]),
        bay=dict(x=-3.5, w=3.0, dp=0.9, f0=2, f1=4, kind='arch', dome=True, trim='M_PlasterRed', parapet='plain'),
        parapet='plain', roof_opts=dict(tanks=2, flag=True, clothesline=True))))
    return V_


# ======================================================================= palaces (Darbhanga / Chet Singh style)
def oct_tower(mb, cx, cy, R, z0, floors, mat, trim, rng, top_chhatri=True, fh=FH, win_kind='cusped', chh_mat=None,
              faces=(0, 1, 2, 3, 4, 5, 6, 7)):
    """Octagonal tower with windows on selected faces (face 0 faces -Y). Returns top z."""
    n = 8
    side = 2 * R * math.sin(math.pi / n)
    apo = R * math.cos(math.pi / n)
    ztop = z0 + floors * fh
    for k in range(n):
        ang = -90 + 45 * k   # outward normal direction angle of face k (deg): k=0 -> -Y
        sub = MB()
        for f in range(floors):
            zz = z0 + f * fh
            ops = []
            if k in faces and f >= 0:
                kd = win_kind if f % 2 == 0 else 'arch'
                w = min(side * 0.5, 1.1)
                op = dict(kind=kd, cx=0.0, sill=zz + 0.8, w=w, h=1.9, depth=0.3, fw=0.09, frame_mat=trim,
                          fill='bars' if rng.random() < 0.5 else None)
                ops += keep_fitting([op], -side / 2, side / 2, zz, zz + fh)
            facade_wall(sub, -side / 2, side / 2, zz, zz + fh, ops, mat)
        # facade frame normal -Y -> rotate so normal points to angle `ang`
        rot = ang + 90
        c = Vector((math.cos(math.radians(ang)) * apo, math.sin(math.radians(ang)) * apo, 0))
        mb.add(sub, T(cx + c.x, cy + c.y, 0) @ Rz(rot))
    ring = regular_poly(8, R, cx, cy, phase=math.radians(-90 - 22.5))
    for f in range(1, floors):
        mb.sweep_path(ring, PROF_BAND, trim, closed=True, z0=z0 + f * fh)
    mb.sweep_path(ring, PROF_CORNICE, trim, closed=True, z0=ztop)
    mb.prism(ring, ztop, ztop + 0.08, trim, bottom=False)
    zt = ztop + 0.08
    # merlons around
    for k in range(8):
        a = math.radians(-90 + 45 * k)
        px, py = cx + math.cos(a) * (apo - 0.15), cy + math.sin(a) * (apo - 0.15)
        sub = MB()
        sub.boxc(0, 0, 0, side * 0.9, 0.25, 0.5, mat)
        mb.add(sub, T(px, py, zt) @ Rz(45 * k))
    if top_chhatri:
        cm = chh_mat or trim
        mb.add(chhatri(size=R * 1.25, n_sides=8, height=R * 1.0, pillar_mat=cm, dome_mat=cm, plinth_h=0.25, seg=24,
                       dome_style='onion'), T(cx, cy, zt))
    return zt


def palace(seed, variant):
    rng = random.Random(seed)
    mb = MB()
    if variant == 1:   # Darbhanga-like: massive sandstone, columns, 7 storeys
        W, D, floors, hp = 32.0, 16.0, 7, 4.0
        mat, trim, pm = 'M_SandstoneRed', 'M_Sandstone', 'M_SandstoneOld'
        upper_mat = 'M_SandstoneRed'
    else:              # Chet Singh-like: fort palace, ochre plaster + sandstone, 6 storeys
        W, D, floors, hp = 28.0, 15.0, 6, 5.0
        mat, trim, pm = 'M_PlasterOchre', 'M_SandstoneRed', 'M_SandstoneRed'
        upper_mat = 'M_PlasterYellow'
    x0, x1 = -W / 2, W / 2
    # --- battered plinth (fort-like base) with arched niches
    base = MB()
    ops = []
    for i in range(7):
        cx = x0 + (i + 0.5) * W / 7
        ops.append(dict(kind='pointed' if variant == 2 else 'arch', cx=cx, sill=0.4, w=1.1, h=hp - 1.4, depth=0.6, fw=0.12,
                        frame_mat=trim, back_mat='M_WindowDark' if i % 2 else pm))
    facade_wall(base, x0 - 0.6, x1 + 0.6, 0.0, hp, keep_fitting(ops, x0 - 0.6, x1 + 0.6, 0, hp), pm)
    mb.add(base, T(0, -0.8, 0))
    mb.box(x0 - 0.6, -0.8, 0, x1 + 0.6, D + 0.3, hp, pm, skip=('-y', '-z'))
    mb.sweep_x(x0 - 0.6, x1 + 0.6, -0.8, [(0, 0), (0.35, 0.0), (0.35, 0.45), (0.0, 1.2)], pm)
    mb.sweep_x(x0 - 0.6, x1 + 0.6, -0.8, [(0, -0.15), (0.1, -0.15), (0.1, 0.0), (0, 0.0)], trim, z0=hp)
    # --- towers at the front corners
    R = 3.0 if variant == 1 else 3.4
    tfl = floors + (1 if variant == 1 else 2)
    tx = W / 2 - R * 0.6
    # --- main block (between towers) with central frontispiece
    style = dict(bay=3.0, win_kinds=['cusped', 'arch'] if variant == 1 else ['pointed', 'rect'],
                 jharokhas=[(2, 1), (2, 8), (4, 1), (4, 8)] if variant == 1 else [(2, 1), (2, 6), (4, 1), (4, 6)],
                 balc_floors=[3] if variant == 1 else [], chhajja_floors=[1, 5] if variant == 1 else [1, 3, 5],
                 ground='arcade', arcade_kind='cusped' if variant == 1 else 'pointed', jhar_mat=trim, jhar_trim=trim,
                 balc_mat=trim, balc_rail_mat=trim, pair_p=0.0, fw=0.13, hood_p=0.6,
                 fills=['bars', 'none', 'glass_grid'], row_kinds={1: 'arch', 5: 'cusped'})
    cw = 9.0 if variant == 1 else 8.0
    main = dict(x0=x0, x1=x1, y0=0.0, y1=D, z0=hp, floors=floors, mat=mat, trim=trim, style=style,
                parapet='merlon' if variant == 2 else 'balustrade', parapet_mat=mat, coping_mat=trim,
                occl=[(-cw / 2, cw / 2, 1, floors - 1)], cornice_mat=trim, floor_mats={floors - 1: upper_mat},
                sides={'front': 'rich', 'left': 'plain', 'right': 'plain', 'back': 'plain'},
                clip=[(-tx - R, -R, -tx + R, R), (tx - R, -R, tx + R, R), (-cw / 2 + 1, 3.0, cw / 2 - 1, 9.0)])
    info = make_block(mb, main, rng)
    ztop = info['ztop']
    # frontispiece: projecting central bay with double-height arcade + balconies
    fdp = 1.6
    fb = dict(x0=-cw / 2, x1=cw / 2, y0=-fdp, y1=0.0, z0=hp + FH - 0.05, floors=floors - 1, fh0=FH + 0.05, mat=trim if variant == 1 else mat,
              trim=trim, style=dict(bay=cw / 3, win_kinds=['cusped'], balc_floors=[2, 4] if variant == 1 else [1, 3],
                                     balc_style='balusters', balc_mat=trim, balc_rail_mat=trim, pair_p=0.0,
                                     jharokhas=[], chhajja_floors=[], row_kinds={i: 'cusped' for i in range(10)}, side_p=1.0, side_bay=fdp,
                                     balc_dp=1.0, cloth_p=0.0, fw=0.14),
              sides={'front': 'rich', 'left': 'plain', 'right': 'plain', 'back': None}, ground=False, bottom=True,
              parapet='pinnacle', parapet_sides=('front', 'left', 'right'), cornice_mat=trim)
    fi = make_block(mb, fb, rng)
    cb = MB()
    corbels(cb, [-cw / 2 + 0.3 + i * (cw - 0.6) / 4 for i in range(5)], fdp, 1.2, trim, w=0.25)
    mb.add(cb, T(0, 0, fb['z0']))
    # pilasters on frontispiece corners
    for sx in (-cw / 2, cw / 2):
        mb.boxc(sx, -fdp, hp + FH, 0.45, 0.45, fi['ztop'], trim)
    # three chhatris above frontispiece
    for cx, s in ((-cw / 2 + 1.3, 2.0), (0.0, 3.2), (cw / 2 - 1.3, 2.0)):
        mb.add(chhatri(size=s, height=s * 0.95, pillar_mat=trim, dome_mat=trim if variant == 1 else 'M_PlasterWhite', seg=24,
                       dome_style='onion' if cx == 0 else 'hemi'), T(cx, -fdp + s / 2 + 0.2, fi['ztop'] + 0.08))
    # --- corner towers
    for sgn in (-1, 1):
        oct_tower(mb, sgn * tx, 0.3, R, hp, tfl, mat if variant == 1 else 'M_PlasterYellow', trim, rng,
                  top_chhatri=True, chh_mat=trim, faces=(0, 1, 7, 2 if sgn > 0 else 6))
    # --- upper storey pavilion set back on the roof
    ub = dict(x0=-W / 2 + 7, x1=W / 2 - 7, y0=4.0, y1=D - 2.0, z0=ztop + 0.08, floors=1, mat=upper_mat, trim=trim,
              style=dict(bay=2.6, win_kinds=['cusped'], balc_floors=[], jharokhas=[], chhajja_floors=[0], pair_p=0.0),
              ground=False, parapet='pinnacle', sides={'front': 'rich', 'left': 'plain', 'right': 'plain', 'back': 'plain'})
    ui = make_block(mb, ub, rng)
    mb.add(dome(2.2, trim if variant == 1 else 'M_PlasterWhite', style='onion', seg=32, lobed=True, drum_h=1.0, drum_mat=trim),
           T(0, (ub['y0'] + ub['y1']) / 2, ui['ztop'] + 0.08))
    roof_clutter(mb, rng, x0 + 1, 10.0, x1 - 1, D - 0.6, ztop + 0.08, mat, trim, dict(mumty=False, tanks=3, flag=True, antenna=False, clothesline=False))
    # side chhatris on main roof rear corners
    for sx in (x0 + 1.4, x1 - 1.4):
        mb.add(chhatri(size=2.0, height=2.0, pillar_mat=trim, dome_mat=trim, seg=20), T(sx, D - 1.4, ztop + 0.08))
    return mb


# ======================================================================= town shop-houses
def town_house(seed, W, D, floors, p):
    rng = random.Random(seed)
    mb = MB()
    x0, x1 = -W / 2, W / 2
    mat = p['mat']
    trim = p.get('trim', 'M_PlasterWhite')
    z0 = 0.3
    # street step / plinth
    mb.box(x0, -0.6, 0, x1, D, z0, 'M_Concrete', skip=('-z',))
    n_shops = p.get('shops', max(1, int(W / 3.2)))
    signs = []

    def shop_floor(sub, u0, u1, zz, hf, rng_, centers, bw):
        ops = []
        sw = (u1 - u0) / n_shops
        for i in range(n_shops):
            a = u0 + i * sw + 0.25
            c = u0 + (i + 1) * sw - 0.25
            cx = (a + c) / 2
            w = c - a
            h = 2.55
            kind = p.get('shop_kinds', ['shutter', 'wood', 'shutter_half', 'open'])[(i + seed) % len(p.get('shop_kinds', [1, 2, 3, 4]))]
            ops.append(dict(kind='rect', cx=cx, sill=zz + 0.06, w=w, h=h, depth=1.6, fw=0.0, back_mat='M_WindowDark',
                            reveal_mat='M_PlasterWorn'))
            # interior: counter + shelves suggestion
            sub.box(a + 0.2, 0.6, zz + 0.06, c - 0.2, 1.0, zz + 0.95, 'M_WoodPlanks')
            sub.box(a + 0.1, 1.45, zz + 1.2, c - 0.1, 1.58, zz + 1.25, 'M_WoodPlanks')
            sub.box(a + 0.1, 1.45, zz + 1.8, c - 0.1, 1.58, zz + 1.85, 'M_WoodPlanks')
            if kind == 'shutter':
                rolling_shutter(sub, a, c, zz + 0.06, zz + h + 0.06, y=0.12, housing=True, y_house=0.0)
            elif kind == 'shutter_half':
                rolling_shutter(sub, a, c, zz + h * rng_.uniform(0.55, 0.8), zz + h + 0.06, y=0.12, housing=True, y_house=0.0)
            elif kind == 'wood':
                # folding wooden shop doors: some panels closed, the rest open
                npan = max(2, int(w / 0.5))
                pw = w / npan
                for k in range(npan):
                    if k < npan // 3:
                        sub.box(a + k * pw + 0.01, 0.1, zz + 0.06, a + (k + 1) * pw - 0.01, 0.14, zz + h + 0.06, 'M_WoodShutter')
                sub.box(a - 0.02, -0.08, zz + h + 0.06, c + 0.02, 0.0, zz + h + 0.2, 'M_WoodShutter')
            else:
                rolling_shutter(sub, a, c, zz + h - 0.15, zz + h + 0.06, y=0.12, housing=True, y_house=0.0)
            # awning
            aw = p.get('awning', ['corr', 'cloth', 'none'])[(i + seed) % len(p.get('awning', [1, 2, 3]))]
            if aw == 'corr':
                awning_corrugated(sub, a - 0.1, c + 0.1, zz + h + 0.5, dp=rng_.uniform(1.0, 1.4), drop=0.35)
            elif aw == 'cloth':
                awning_cloth(sub, a, c, zz + h + 0.45, dp=rng_.uniform(1.1, 1.5), drop=0.4,
                             mat='M_Cloth')
            # signboard above
            sz0 = zz + h + 0.62
            signboard(sub, a + 0.05, c - 0.05, sz0, min(sz0 + 0.75, zz + hf + 0.25), y=-0.14)
        return ops

    style = dict(bay=p.get('bay', 2.8), win_kinds=p.get('win_kinds', ['rect']), balc_floors=p.get('balc_floors', [1]),
                 balc_style=p.get('balc_style', 'iron'), chhajja_floors=p.get('chhajja_floors', [2]), cloth_p=0.6,
                 fills=['bars', 'bars', 'half_shutter', 'shutters'], hood_p=0.5, pair_p=0.2, jharokhas=p.get('jharokhas', []),
                 jhar_mat=trim)
    b = dict(x0=x0, x1=x1, y0=0.0, y1=D, z0=z0, floors=floors, fh0=3.6, mat=mat, trim=trim, style=style,
             floor_mats=p.get('floor_mats', {}), parapet=p.get('parapet', 'plain'), parapet_h=1.0,
             sides=p.get('sides', {'front': 'rich', 'left': 'none', 'right': 'none', 'back': 'plain'}),
             custom={('front', 0): shop_floor}, clip=[], cornice_prof=p.get('cornice_prof', PROF_CORNICE))
    upper = None
    if p.get('extra_floor'):
        ef = p['extra_floor']
        upper = dict(x0=x0 + ef.get('left', 0), x1=x1 - ef.get('right', 0), y0=ef.get('front', 1.5), y1=D, z0=0,
                     floors=1, mat=ef.get('mat', 'M_BrickPlaster'), trim=trim,
                     style=dict(style, balc_floors=[], jharokhas=[], chhajja_floors=[]), ground=False, parapet=None,
                     cornice=False, sides={'front': 'rich', 'left': 'none', 'right': 'none', 'back': 'plain'})
        b['clip'] = [(upper['x0'], upper['y0'], upper['x1'], upper['y1'])]
    info = make_block(mb, b, rng)
    zt = info['ztop'] + 0.08
    if upper:
        upper['z0'] = zt
        ui = make_block(mb, upper, rng)
        rt = ui['ztop']
        roof_clutter(mb, rng, upper['x0'] + 0.3, upper['y0'] + 0.3, upper['x1'] - 0.3, upper['y1'] - 0.3, rt, mat, trim,
                     dict(mumty=False, tanks=2, rebar=True, flag=False, clothesline=False))
        roof_clutter(mb, rng, x0 + 0.4, 0.4, x1 - 0.4, upper['y0'] - 0.2, zt, mat, trim,
                     dict(mumty=False, tanks=0, antenna=False, flag=False, clothesline=True))
    else:
        roof_clutter(mb, rng, x0 + 0.3, 0.3, x1 - 0.3, D - 0.3, zt, mat, trim,
                     dict(p.get('roof_opts', {})))
    # wire hooks + electric meter boxes + AC units
    for i in range(p.get('hooks', 3)):
        wire_hook(mb, rng.uniform(x0 + 0.4, x1 - 0.4), z0 + 3.6 + rng.uniform(1.2, 1.7), 0.0)
    for i in range(p.get('ac', 1)):
        ax = rng.uniform(x0 + 0.8, x1 - 0.8)
        az = z0 + 3.6 + FH * rng.randint(0, max(0, floors - 2)) + 2.6
        mb.box(ax - 0.45, -0.35, az, ax + 0.45, 0.0, az + 0.6, 'M_Concrete')
        mb.box(ax - 0.35, -0.36, az + 0.1, ax + 0.35, -0.35, az + 0.5, 'M_MetalRust')
    mb.box(x0 + 0.3, -0.18, z0 + 1.6, x0 + 0.75, 0.0, z0 + 2.2, 'M_MetalRust')   # meter box
    return mb


def TOWN_VARIANTS():
    T_ = []
    T_.append(('Bldg_Town_01', 2101, 7.0, 10.0, 3, dict(mat='M_PlasterYellow', trim='M_PlasterWhite', shops=2,
               floor_mats={0: 'M_PlasterDamaged'}, balc_floors=[1], shop_kinds=['shutter_half', 'open'], awning=['corr', 'cloth'])))
    T_.append(('Bldg_Town_02', 2202, 6.0, 9.0, 2, dict(mat='M_PlasterBlue', trim='M_PlasterWhite', shops=1, balc_floors=[1],
               shop_kinds=['wood'], awning=['cloth'], extra_floor=dict(front=2.0, mat='M_BrickPlaster'))))
    T_.append(('Bldg_Town_03', 2303, 9.0, 11.0, 4, dict(mat='M_PlasterPainted', trim='M_PlasterWhite', shops=3,
               floor_mats={0: 'M_PlasterWorn', 3: 'M_BrickPlaster'}, balc_floors=[1, 2], shop_kinds=['shutter', 'open', 'shutter_half'],
               awning=['corr', 'none', 'corr'], roof_opts=dict(tanks=2, rebar=True))))
    T_.append(('Bldg_Town_04', 2404, 5.5, 10.0, 3, dict(mat='M_PlasterOchre', trim='M_PlasterWhite', shops=1, balc_floors=[2],
               win_kinds=['arch'], shop_kinds=['open'], awning=['corr'], chhajja_floors=[1], parapet='pinnacle')))
    T_.append(('Bldg_Town_05', 2505, 8.0, 12.0, 2, dict(mat='M_PlasterWhite', trim='M_PlasterBlue', shops=2, balc_floors=[],
               chhajja_floors=[1], shop_kinds=['shutter_half', 'wood'], awning=['cloth', 'corr'],
               extra_floor=dict(front=3.0, left=2.0, mat='M_PlasterPeeling'))))
    T_.append(('Bldg_Town_06', 2606, 10.0, 12.0, 3, dict(mat='M_PlasterRed', trim='M_PlasterWhite', shops=3, balc_floors=[1],
               balc_style='balusters', win_kinds=['arch', 'rect'], jharokhas=[(2, 1)], shop_kinds=['open', 'shutter', 'wood'],
               awning=['cloth', 'corr', 'none'], floor_mats={0: 'M_PlasterMossy'}, roof_opts=dict(tanks=2, flag=True))))
    T_.append(('Bldg_Town_07', 2707, 6.5, 9.0, 4, dict(mat='M_PlasterPeeling', trim='M_PlasterYellow', shops=2, balc_floors=[1, 3],
               shop_kinds=['shutter', 'shutter_half'], awning=['corr', 'corr'], floor_mats={2: 'M_PlasterYellow', 3: 'M_PlasterYellow'},
               roof_opts=dict(tanks=3, rebar=True, antenna=True))))
    T_.append(('Bldg_Town_08', 2808, 12.0, 10.0, 2, dict(mat='M_ClayPlaster', trim='M_PlasterWhite', shops=4, balc_floors=[1],
               balc_style='solid', shop_kinds=['open', 'shutter_half', 'wood', 'shutter'], awning=['corr', 'cloth', 'corr', 'none'],
               roof_opts=dict(tanks=2, clothesline=True, rebar=True))))
    return T_
