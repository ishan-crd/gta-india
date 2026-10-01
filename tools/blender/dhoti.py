"""dhoti.py - procedural dhoti / mundu (white wrap with a gold kasavu border) for gi_build_char.py.

Used by gi_build_char.py --dhoti <bottom slot>: the trousers mesh of that material slot is measured (its
waist/hip silhouette gives the cloth's cross-section), deleted, and replaced by a closed wrap from the
waist (tucked under the shirt given by --dhoti-under) down to a few cm above the floor, with soft folds,
a front overlap flap, a gold border band along the hem and the flap's vertical edge, a cloth thickness
(solidify, so the inside is visible from below) and smooth skirt skin weights
(Hips -> UpLeg -> Leg by height, left/right by side with a wide centre blend so it never tears).

Coordinates: the call happens after gi_build_char normalised the mesh (metres, feet on Z=0, Hips over the
origin, character faces -Y, left = +X) and before the canonical armature is built; vertex groups use the
canonical (Mixamo) names.
"""
import bpy, bmesh, math, os, re
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

BAND = 0.04           # hem border band width (m)
BAND_EDGE = 0.03      # border band width along the flap's vertical edge (m)
HEM = 0.045           # hem height above the floor (m)
THICK = 0.004         # cloth thickness (m)
ROW = 0.025           # vertical row spacing (m)
NCOL = 64             # columns around the tube
FLAP_EDGE = -0.36     # angle of the flap's free (bordered) edge; 0 = front (-Y), + = toward the left (+X)
FLAP_SPAN = 2.0       # radians the flap wraps from its edge toward the left side
TILE = 0.45           # cloth texture tile size (m)


def _smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _slot_indices(obj, name):
    return [i for i, s in enumerate(obj.material_slots)
            if s.material and re.sub(r"\.\d{3}$", "", s.material.name) == name]


def _verts_of_slots(me, idx):
    vi = set()
    for p in me.polygons:
        if p.material_index in idx:
            vi.update(p.vertices)
    return np.array(sorted(vi), dtype=np.int64)


# ------------------------------------------------------------------------------------------- textures
def _blur_periodic(a, sigma_px):
    h, w = a.shape
    fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.fftfreq(w)[None, :]
    g = np.exp(-2 * (math.pi * sigma_px) ** 2 * (fx * fx + fy * fy))
    return np.real(np.fft.ifft2(np.fft.fft2(a) * g))


def _save(name, rgb, path):
    h, w, _ = rgb.shape
    px = np.ones((h, w, 4), dtype=np.float32)
    px[:, :, :3] = np.clip(rgb, 0, 1)
    img = bpy.data.images.new(name, w, h, alpha=False)
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    img.colorspace_settings.name = 'sRGB'
    return img


def make_textures(out_dir, size=1024, seed=7):
    """tileable off-white cotton (subtle weave + noise + faint vertical creases) and a gold kasavu border."""
    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng(seed)
    n = size
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    # weave: fine warp/weft threads (period 4 px) modulated by slub noise
    weave = 0.5 * (np.sin(xx * math.pi / 2) * np.sin(yy * math.pi / 2))
    slub = _blur_periodic(rng.standard_normal((n, n)), 1.2)
    slub /= np.abs(slub).max() + 1e-6
    blot = _blur_periodic(rng.standard_normal((n, n)), 40)
    blot /= np.abs(blot).max() + 1e-6
    # vertical creases: functions of u (columns), slowly wandering along v (rows)
    crease = np.zeros((n, n), np.float32)
    for _ in range(9):
        c0 = rng.uniform(0, n); wid = rng.uniform(4, 22); amp = rng.uniform(0.25, 1.0)
        wander = 6 * np.sin(2 * math.pi * (yy / n) * rng.integers(1, 3) + rng.uniform(0, 6.3))
        d = (xx - c0 - wander + n / 2) % n - n / 2
        crease += amp * np.exp(-0.5 * (d / wid) ** 2)
    crease /= crease.max() + 1e-6
    lum = 1.0 + 0.018 * weave + 0.03 * slub + 0.025 * blot - 0.045 * crease
    base = np.array([0.93, 0.925, 0.89], np.float32)
    cloth = base[None, None, :] * lum[:, :, None]
    cloth_p = os.path.join(out_dir, "dhoti_cloth.png")
    _save("dhoti_cloth", cloth, cloth_p)

    # border: u = along the band (columns), v = across the band (rows, 0 = outer edge)
    v = (yy + 0.5) / n
    gold = np.array([0.88, 0.63, 0.18], np.float32)
    dark = np.array([0.62, 0.38, 0.08], np.float32)
    line = np.zeros_like(v)
    for c, w in ((0.10, 0.018), (0.86, 0.022), (0.93, 0.012)):
        line = np.maximum(line, np.exp(-0.5 * ((v - c) / w) ** 2))
    sheen = 1.0 + 0.05 * np.sin(xx * math.pi / 2) * np.sin(yy * math.pi / 3) + 0.04 * slub
    border = (gold[None, None, :] * (1 - line[:, :, None]) + dark[None, None, :] * line[:, :, None]) * sheen[:, :, None]
    border_p = os.path.join(out_dir, "dhoti_border.png")
    _save("dhoti_border", border, border_p)
    return cloth_p, border_p


def _material(name, tex_path, rough):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(nd for nd in nt.nodes if nd.type == 'BSDF_PRINCIPLED')
    tx = nt.nodes.new('ShaderNodeTexImage')
    tx.image = bpy.data.images.load(tex_path, check_existing=True)
    tx.image.colorspace_settings.name = 'sRGB'
    nt.links.new(tx.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    return m


# ------------------------------------------------------------------------------------------- shape
def _polar_profile(pts, cy, z_rows, nbins=72):
    """max radial distance of pts per (row, angle bin); empty bins filled circularly."""
    ang = np.arctan2(pts[:, 0], -(pts[:, 1] - cy))            # 0 = front (-Y), + toward +X
    rad = np.hypot(pts[:, 0], pts[:, 1] - cy)
    b = ((ang % (2 * math.pi)) / (2 * math.pi) * nbins).astype(int) % nbins
    out = np.full((len(z_rows), nbins), np.nan)
    for i, z in enumerate(z_rows):
        m = np.abs(pts[:, 2] - z) < 0.02
        if not m.any():
            continue
        r = np.full(nbins, np.nan)
        for k in np.unique(b[m]):
            r[k] = rad[m][b[m] == k].max()
        good = ~np.isnan(r)
        if good.sum() < 3:
            continue
        idx = np.arange(nbins)
        gi = idx[good]
        r = np.interp(idx, np.concatenate([gi - nbins, gi, gi + nbins]), np.tile(r[good], 3))
        r = np.maximum(r, np.maximum(np.roll(r, 1), np.roll(r, -1)))   # dilate one bin
        out[i] = r
    # rows without points: nearest row that has some
    have = [i for i in range(len(z_rows)) if not np.isnan(out[i]).any()]
    for i in range(len(z_rows)):
        if np.isnan(out[i]).any():
            j = min(have, key=lambda k: abs(k - i))
            out[i] = out[j]
    return out


def _sample_bins(prof, theta):
    nb = prof.shape[-1]
    f = (theta % (2 * math.pi)) / (2 * math.pi) * nb - 0.5
    i0 = np.floor(f).astype(int) % nb; i1 = (i0 + 1) % nb; t = f - np.floor(f)
    return prof[..., i0] * (1 - t) + prof[..., i1] * t


def _folds(theta, z, s, seed=3):
    rng = np.random.default_rng(seed)
    out = 0.0
    for n_, a_ in ((5, 0.35), (8, 0.3), (13, 0.22), (19, 0.13)):
        ph = rng.uniform(0, 6.3); k = rng.uniform(-6, 6)
        out = out + a_ * np.sin(n_ * theta + ph + k * z)
    amp = 0.003 + 0.013 * s ** 0.8
    return amp * out


def add_shins(body, J, skin_slot="AvatarBody", top_below_knee=0.08):
    """the trousers hid legless bodies: add simple shins + knees (ankle -> just above the knee) textured with a
    forearm patch of the body's skin texture, so a lifted hem shows a leg instead of a floating shoe."""
    me = body.data
    sidx = _slot_indices(body, skin_slot)
    if not sidx:
        print("dhoti: no skin slot", skin_slot, "- no shins"); return 0
    uvd = me.uv_layers.active.data
    # skin UV: body-material loop nearest the middle of the left forearm
    target = (J["LeftForeArm"] + J["LeftHand"]) * 0.5
    best, buv = 1e9, None
    for p in me.polygons:
        if p.material_index not in sidx:
            continue
        for li in p.loop_indices:
            d = (me.vertices[me.loops[li].vertex_index].co - target).length
            if d < best:
                best, buv = d, uvd[li].uv.copy()
    zK = J["LeftLeg"].z
    shoes_top = 0.12
    zs = [shoes_top, 0.16, 0.22, 0.30, zK - top_below_knee]     # shins only: knees/thighs would poke the cloth
    rr = [0.033, 0.035, 0.041, 0.045, 0.043]
    nseg = 12
    verts, faces = [], []
    wts = []
    for side in ("Left", "Right"):
        cx, cy_ = J[side + "Leg"].x, J[side + "Leg"].y
        base = len(verts)
        for z, r in zip(zs, rr):
            for k in range(nseg):
                a_ = 2 * math.pi * k / nseg
                verts.append((cx + r * math.sin(a_), cy_ - r * math.cos(a_) * 1.05, z))
                wl = float(1 - _smooth(zK - 0.05, zK + 0.05, np.array(z)))
                wts.append({side + "Leg": wl, side + "UpLeg": 1 - wl})
        for i in range(len(zs) - 1):
            for k in range(nseg):
                k1 = (k + 1) % nseg
                a0 = base + i * nseg
                faces.append((a0 + k, a0 + nseg + k, a0 + nseg + k1, a0 + k1))
    lm = bpy.data.meshes.new("shins")
    lm.from_pydata(verts, [], faces); lm.update()
    uvl = lm.uv_layers.new(name=me.uv_layers.active.name)
    for p in lm.polygons:          # tiny non-degenerate patch around the skin texel (sane tangents)
        for li in p.loop_indices:
            vi = lm.loops[li].vertex_index
            k, i = vi % nseg, (vi // nseg) % len(zs)
            uvl.data[li].uv = (buv[0] + 0.0005 * k, buv[1] + 0.0008 * i)
    lo = bpy.data.objects.new("shins", lm)
    bpy.context.scene.collection.objects.link(lo)
    lm.materials.append(body.material_slots[sidx[0]].material)
    bm = bmesh.new(); bm.from_mesh(lm)
    bm.faces.ensure_lookup_table()
    f = bm.faces[0]; c = f.calc_center_median()
    radial = Vector((c.x - J["LeftLeg"].x * (1 if c.x > 0 else -1), c.y - J["LeftLeg"].y, 0))
    if f.normal.dot(radial) < 0:
        for f in bm.faces:
            f.normal_flip()
    bm.to_mesh(lm); bm.free()
    for p in lm.polygons:
        p.use_smooth = True
    for vi, w in enumerate(wts):
        for n_, x in w.items():
            if x > 1e-3:
                vg = lo.vertex_groups.get(n_) or lo.vertex_groups.new(name=n_)
                vg.add([vi], x, 'REPLACE')
    with bpy.context.temp_override(selected_objects=[body, lo], selected_editable_objects=[body, lo],
                                   active_object=body, object=body):
        bpy.ops.object.join()
    print("dhoti: shins added, skin uv", tuple(buv), "dist", round(best, 3))
    return len(faces) * 2


def build(body, J, bottom_slot, under_slot="", cloth_tex="", border_tex="", prefix="dhoti", shins=True):
    """replace the trousers (material slot bottom_slot) of the joined, normalised body mesh with a dhoti."""
    me = body.data
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    bidx = _slot_indices(body, bottom_slot)
    if not bidx:
        raise SystemExit(f"--dhoti: no material slot named {bottom_slot}")
    jeans = co[_verts_of_slots(me, bidx)]
    top_idx = _slot_indices(body, under_slot) if under_slot else []
    shirt_vi = _verts_of_slots(me, top_idx) if top_idx else np.array([], np.int64)

    zH = J["LeftUpLeg"].z; zK = J["LeftLeg"].z; zA = J["LeftFoot"].z
    z_top = float(jeans[:, 2].max()) - 0.015
    hipband = jeans[(jeans[:, 2] > zH - 0.12) & (jeans[:, 2] < zH + 0.05)]
    cy = 0.5 * (hipband[:, 1].min() + hipband[:, 1].max())
    z_rows = [z_top]
    while z_rows[-1] - ROW > HEM + BAND + 0.012:
        z_rows.append(z_rows[-1] - ROW)
    z_rows += [HEM + BAND, HEM]
    z_rows = np.array(z_rows)
    nr = len(z_rows)
    prof = _polar_profile(jeans, cy, z_rows)                          # (nr, 72)
    marg = 0.008 + 0.012 * _smooth(z_top, zH - 0.05, z_rows)          # tight at the waist, 2 cm at the hips
    base = prof + marg[:, None]
    base = np.maximum.accumulate(base, axis=0)                        # never narrower going down
    s_rows = np.clip((zH - z_rows) / (zH - HEM), 0, 1)
    base *= (1 + 0.06 * s_rows ** 1.4)[:, None]                       # gentle flare toward the hem
    # smooth around (circular) and down
    for _ in range(3):
        base = 0.25 * np.roll(base, 1, 1) + 0.5 * base + 0.25 * np.roll(base, -1, 1)
    base[1:-1] = np.maximum(base[1:-1], 0.25 * base[:-2] + 0.5 * base[1:-1] + 0.25 * base[2:])

    # shirt cap: under the shirt the cloth stays just inside it, then relaxes outward below the hem
    shirt_bvh = None
    if len(shirt_vi):
        polys = [list(p.vertices) for p in me.polygons if p.material_index in top_idx]
        shirt_bvh = BVHTree.FromPolygons([Vector(c) for c in co], polys, all_triangles=False)

    def capped(TH, EX):
        """TH, EX: (nr, ncol) angles and extra radial offsets -> radii with folds and the shirt cap."""
        R = np.zeros(TH.shape)
        for i in range(nr):
            s = float(np.clip((zH + 0.02 - z_rows[i]) / (zH + 0.02 - HEM), 0, 1))
            R[i] = _sample_bins(base[i], TH[i]) + _folds(TH[i], z_rows[i], s) + EX[i]
        if shirt_bvh is None:
            return R
        for j in range(TH.shape[1]):
            last = None
            for i in range(nr):
                th = TH[i, j]
                d = Vector((math.sin(th), -math.cos(th), 0.0))
                o = Vector((0.0, cy, z_rows[i]))
                hit = shirt_bvh.ray_cast(o, d, 1.0)
                if hit[0] is not None:
                    rh = (hit[0] - o).length
                    floor_r = _sample_bins(prof[i], np.array([th]))[0] + 0.002
                    R[i, j] = max(min(R[i, j], rh - 0.007 + min(EX[i, j], 0.004)), min(floor_r, rh - 0.003))
                    last = (R[i, j], z_rows[i])
                elif last is not None:
                    R[i, j] = min(R[i, j], last[0] + 0.45 * (last[1] - z_rows[i]))
        return R

    verts, faces, fmat, fuv = [], [], [], []

    def grid(TH, R, closed):
        """TH: (nr, ncol) angles, R: (nr, ncol) radii -> vertex ids (nr, ncol)."""
        ids = np.zeros(TH.shape, int)
        for i in range(nr):
            for j in range(TH.shape[1]):
                ids[i, j] = len(verts)
                verts.append((R[i, j] * math.sin(TH[i, j]), cy - R[i, j] * math.cos(TH[i, j]), z_rows[i]))
        return ids

    rmean = float(base[nr // 2].mean())
    reps = max(1, round(2 * math.pi * rmean / TILE))

    def quad(a, b, c, d, mat, uvs):
        faces.append((a, b, c, d)); fmat.append(mat); fuv.append(uvs)

    # ---- main tube
    th = np.arange(NCOL) * 2 * math.pi / NCOL
    R = capped(np.tile(th, (nr, 1)), np.zeros((nr, NCOL)))
    ids = grid(np.tile(th, (nr, 1)), R, True)
    tube_faces0 = len(faces)
    for i in range(nr - 1):
        hem = i == nr - 2
        for j in range(NCOL):
            j1 = (j + 1) % NCOL
            uj, uj1 = j / NCOL, (j + 1) / NCOL
            if hem:
                ub0, ub1 = uj * 2 * math.pi * rmean / 0.3, uj1 * 2 * math.pi * rmean / 0.3
                uvs = [(ub0, 1), (ub1, 1), (ub1, 0), (ub0, 0)]
                m = 1
            else:
                v0, v1 = z_rows[i] / TILE, z_rows[i + 1] / TILE
                uvs = [(uj * reps, v0), (uj1 * reps, v0), (uj1 * reps, v1), (uj * reps, v1)]
                m = 0
            quad(ids[i, j], ids[i, j1], ids[i + 1, j1], ids[i + 1, j], m, uvs)
    tube_faces1 = len(faces)

    # ---- overlap flap: free edge at FLAP_EDGE (gold band), wraps toward the left side, sinks into the tube
    nfc = 22
    TH = np.zeros((nr, nfc + 2))
    for i in range(nr):
        rb = float(_sample_bins(base[i], np.array([FLAP_EDGE]))[0])
        tb = FLAP_EDGE + BAND_EDGE / rb
        TH[i, 0] = FLAP_EDGE; TH[i, 1] = tb
        TH[i, 2:] = tb + (np.arange(1, nfc + 1) / nfc) * (FLAP_EDGE + FLAP_SPAN - tb)
    frac = (TH - FLAP_EDGE) / FLAP_SPAN
    EX = 0.0075 * (1 - _smooth(0.55, 1.0, frac)) - 0.002 * _smooth(0.85, 1.0, frac)
    RF = capped(TH, EX)
    # flap hem a few mm lower than the tube's so the bands do not z-fight
    fids = grid(TH, RF, False)
    for j in range(TH.shape[1]):
        vx = verts[fids[nr - 1, j]]
        verts[fids[nr - 1, j]] = (vx[0], vx[1], vx[2] - 0.004)
    for i in range(nr - 1):
        hem = i == nr - 2
        for j in range(TH.shape[1] - 1):
            a_, b_ = TH[i, j], TH[i, j + 1]
            if j == 0:
                # vertical border band: u along the edge (height), v across (0 = free edge)
                u0, u1 = z_rows[i] / 0.3, z_rows[i + 1] / 0.3
                uvs = [(u0, 0), (u0, 1), (u1, 1), (u1, 0)]
                m = 1
            elif hem:
                ub0, ub1 = a_ * rmean / 0.3, b_ * rmean / 0.3
                uvs = [(ub0, 1), (ub1, 1), (ub1, 0), (ub0, 0)]
                m = 1
            else:
                v0, v1 = z_rows[i] / TILE, z_rows[i + 1] / TILE
                ua, ub = a_ / (2 * math.pi) * reps, b_ / (2 * math.pi) * reps
                uvs = [(ua, v0), (ub, v0), (ub, v1), (ua, v1)]
                m = 0
            quad(fids[i, j], fids[i, j + 1], fids[i + 1, j + 1], fids[i + 1, j], m, uvs)

    # ---- keep everything under the shirt strictly inside it (nearest-surface push, radial)
    if shirt_bvh is not None:
        zmin_shirt = float(co[shirt_vi, 2].min())
        nflap0 = int(fids.min())
        for it in range(3):
            moved = 0
            for k, (vx, vy, vz) in enumerate(verts):
                if vz < zmin_shirt - 0.01:
                    continue
                p = Vector((vx, vy, vz))
                loc, nrm, _, dist = shirt_bvh.find_nearest(p)
                if loc is None or dist > 0.04:
                    continue
                rad = Vector((loc.x, loc.y - cy, 0.0))
                if rad.length < 1e-6:
                    continue
                rad.normalize()
                m = 0.003 if k >= nflap0 else 0.006
                sd = (p - loc).dot(rad)
                if sd > -m + 1e-5:
                    p -= rad * (sd + m)
                    verts[k] = (p.x, p.y, p.z); moved += 1
            if not moved:
                break
            print("dhoti: pushed", moved, "verts under the shirt (pass", it, ")")

    # ---- mesh object
    dm = bpy.data.meshes.new(prefix)
    dm.from_pydata(verts, [], faces)
    dm.update()
    uvl = dm.uv_layers.new(name="UVMap")
    for p, m, uvs in zip(dm.polygons, fmat, fuv):
        p.material_index = m
        for k, li in enumerate(p.loop_indices):
            uvl.data[li].uv = uvs[k]
    # outward normals (faces wound with increasing angle: check and flip if inward)
    bm = bmesh.new(); bm.from_mesh(dm)
    bm.faces.ensure_lookup_table()
    f = bm.faces[(tube_faces0 + tube_faces1) // 2]
    c = f.calc_center_median()
    radial = Vector((c.x, c.y - cy, 0)).normalized()
    if f.normal.dot(radial) < 0:
        for f in bm.faces:
            f.normal_flip()
    bm.to_mesh(dm); bm.free()
    do = bpy.data.objects.new(prefix, dm)
    bpy.context.scene.collection.objects.link(do)
    dm.materials.append(_material(prefix + "_cloth", cloth_tex, 0.9))
    dm.materials.append(_material(prefix + "_border", border_tex, 0.5))
    sm = do.modifiers.new("solid", 'SOLIDIFY')
    sm.thickness = THICK; sm.offset = -1.0; sm.use_rim = True; sm.use_even_offset = True
    with bpy.context.temp_override(selected_objects=[do], selected_editable_objects=[do], active_object=do, object=do):
        bpy.ops.object.modifier_apply(modifier="solid")
    for p in dm.polygons:
        p.use_smooth = True

    # ---- skin weights
    dco = np.array([v.co[:] for v in dm.vertices])
    x, z = dco[:, 0], dco[:, 2]
    u = (zH - z) / (zH - zA)
    wh = 1 - _smooth(-0.06, 0.30, u)                 # hips share: waist -> mid thigh
    wl = _smooth(0.25, 0.78, u)                      # of the leg share: thigh -> calf (hem rigid with the calf)
    sL = _smooth(-0.075, 0.075, x)                   # wide centre blend
    W = {"Hips": wh,
         "LeftUpLeg": (1 - wh) * (1 - wl) * sL, "LeftLeg": (1 - wh) * wl * sL,
         "RightUpLeg": (1 - wh) * (1 - wl) * (1 - sL), "RightLeg": (1 - wh) * wl * (1 - sL)}
    if len(shirt_vi):
        # under the shirt: copy the shirt's own weights so cloth and shirt hem move together
        kd = KDTree(len(shirt_vi))
        for k, vi in enumerate(shirt_vi):
            kd.insert(Vector(co[vi]), k)
        kd.balance()
        gname = {g.index: g.name for g in body.vertex_groups}
        for vi_, (px, py, pz) in enumerate(dco):
            near = kd.find_n(Vector((px, py, pz)), 6)
            dmin = near[0][2] if near else 1.0
            b = float(1 - _smooth(0.02, 0.06, np.array(dmin)))
            if b <= 0:
                continue
            acc = {}
            tw = 0.0
            for (_, k, dist) in near:
                iw = 1.0 / (dist + 0.005); tw += iw
                for g in me.vertices[int(shirt_vi[k])].groups:
                    n_ = gname[g.group]
                    acc[n_] = acc.get(n_, 0.0) + iw * g.weight
            for n_ in set(acc) | set(W):
                if n_ not in W:
                    W[n_] = np.zeros(len(dco))
                W[n_][vi_] = (1 - b) * W[n_][vi_] + b * acc.get(n_, 0.0) / tw
    tot = sum(W.values()) + 1e-9
    for n_, w in W.items():
        vg = do.vertex_groups.new(name=n_)
        w = w / tot
        for vi_ in np.nonzero(w > 1e-3)[0]:
            vg.add([int(vi_)], float(w[vi_]), 'REPLACE')

    # ---- remove the trousers, then merge the dhoti into the body
    bm = bmesh.new(); bm.from_mesh(me)
    dead = set()
    for f in bm.faces:
        if f.material_index in bidx:
            dead.update(f.verts)
    bmesh.ops.delete(bm, geom=list(dead), context='VERTS')
    bm.to_mesh(me); bm.free()
    for i in sorted(bidx, reverse=True):
        body.active_material_index = i
        with bpy.context.temp_override(object=body, active_object=body):
            bpy.ops.object.material_slot_remove()
    ntris = sum(len(p.vertices) - 2 for p in dm.polygons)
    with bpy.context.temp_override(selected_objects=[body, do], selected_editable_objects=[body, do],
                                   active_object=body, object=body):
        bpy.ops.object.join()
    if shins:
        ntris += add_shins(body, J)
    print("dhoti: rows", nr, "top %.3f hem %.3f cy %.3f" % (z_top, HEM, cy), "tris", ntris,
          "removed trouser verts", len(dead))
    return ntris
