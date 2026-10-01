"""
kit_core.py - low level procedural mesh building for the GTA India Varanasi kit.

All geometry is authored in METRES, Z up, in "Blender authoring space":
  * buildings: front facade faces -Y (towards the river), facade wall plane at Y=0
  * steps: water edge at Y=0, rising towards +Y
The exporter (kit_export.py) bakes a 180deg Z rotation so that after UE's FBX
import (which mirrors Y) the assets face -Y in UE as well.  See kit_export.py.

MB (mesh builder) collects polygons with a material slot name per face.
Faces are stored with their own vertices and welded at finalize time.
"""
import math
from mathutils import Vector, Matrix
from mathutils.geometry import tessellate_polygon

TAU = math.tau


def V(*a):
    if len(a) == 1:
        a = a[0]
    return Vector((float(a[0]), float(a[1]), float(a[2]) if len(a) > 2 else 0.0))


def newell(pts):
    n = Vector((0.0, 0.0, 0.0))
    k = len(pts)
    for i in range(k):
        a = pts[i]
        b = pts[(i + 1) % k]
        n.x += (a.y - b.y) * (a.z + b.z)
        n.y += (a.z - b.z) * (a.x + b.x)
        n.z += (a.x - b.x) * (a.y + b.y)
    return n


def area2d(poly):
    s = 0.0
    for i in range(len(poly)):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % len(poly)]
        s += x0 * y1 - x1 * y0
    return s * 0.5


def ccw(poly):
    return poly if area2d(poly) >= 0 else list(reversed(poly))


class MB:
    """Mesh builder."""

    def __init__(self):
        self.v = []      # Vector
        self.f = []      # list of vertex index lists
        self.m = []      # material slot name per face
        self.uvo = []    # per face: None or planar uv override (origin, u, v, w, h)

    # ------------------------------------------------------------ basics
    def _add(self, pts, mat, uvo=None):
        base = len(self.v)
        self.v.extend(pts)
        self.f.append(list(range(base, base + len(pts))))
        self.m.append(mat)
        self.uvo.append(uvo)

    def face(self, pts, mat, normal=None, center=None, uvo=None):
        """Add a planar polygon. Orientation fixed to `normal`, or away from `center`."""
        pts = [p if isinstance(p, Vector) else V(p) for p in pts]
        if len(pts) < 3:
            return
        n = newell(pts)
        if n.length < 1e-12:
            return
        if normal is not None:
            if n.dot(V(normal)) < 0:
                pts.reverse()
        elif center is not None:
            c = sum(pts, Vector()) / len(pts)
            if n.dot(c - V(center)) < 0:
                pts.reverse()
        self._add(pts, mat, uvo)

    def face_holes(self, outer, holes, normal, mat):
        """Planar polygon with holes, triangulated. All points 3D and coplanar."""
        outer = [p if isinstance(p, Vector) else V(p) for p in outer]
        holes = [[p if isinstance(p, Vector) else V(p) for p in h] for h in holes]
        allp = outer + [p for h in holes for p in h]
        tris = tessellate_polygon([[tuple(p) for p in outer]] + [[tuple(p) for p in h] for h in holes])
        n = V(normal)
        for t in tris:
            a, b, c = allp[t[0]], allp[t[1]], allp[t[2]]
            cr = (b - a).cross(c - a)
            if cr.length < 1e-10:
                continue
            if cr.dot(n) < 0:
                a, c = c, a
            self._add([a.copy(), b.copy(), c.copy()], mat)

    def add(self, other, M=None):
        """Merge another builder, optionally transformed by 4x4 matrix M."""
        base = len(self.v)
        if M is None:
            self.v.extend(v.copy() for v in other.v)
            mirrored = False
        else:
            self.v.extend(M @ v for v in other.v)
            mirrored = M.to_3x3().determinant() < 0
        for f, m, u in zip(other.f, other.m, other.uvo):
            idx = [i + base for i in f]
            if mirrored:
                idx.reverse()
            if u is not None and M is not None:
                o, uu, vv, w, h = u
                R = M.to_3x3()
                u = (M @ o, (R @ uu).normalized(), (R @ vv).normalized(), w, h)
            self.f.append(idx)
            self.m.append(m)
            self.uvo.append(u)

    def transform(self, M):
        for i, v in enumerate(self.v):
            self.v[i] = M @ v
        if M.to_3x3().determinant() < 0:
            self.f = [list(reversed(f)) for f in self.f]

    def replace_mat(self, old, new):
        self.m = [new if m == old else m for m in self.m]

    def tri_count(self):
        return sum(len(f) - 2 for f in self.f)

    def bounds(self):
        xs = [v.x for v in self.v]
        ys = [v.y for v in self.v]
        zs = [v.z for v in self.v]
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))

    # ------------------------------------------------------------ solids
    def box(self, x0, y0, z0, x1, y1, z1, mat, skip=(), mats=None):
        if x0 > x1: x0, x1 = x1, x0
        if y0 > y1: y0, y1 = y1, y0
        if z0 > z1: z0, z1 = z1, z0
        if x1 - x0 < 1e-6 or y1 - y0 < 1e-6 or z1 - z0 < 1e-6:
            return
        P = V
        faces = {
            '-y': ([P(x0, y0, z0), P(x1, y0, z0), P(x1, y0, z1), P(x0, y0, z1)], (0, -1, 0)),
            '+y': ([P(x1, y1, z0), P(x0, y1, z0), P(x0, y1, z1), P(x1, y1, z1)], (0, 1, 0)),
            '-x': ([P(x0, y1, z0), P(x0, y0, z0), P(x0, y0, z1), P(x0, y1, z1)], (-1, 0, 0)),
            '+x': ([P(x1, y0, z0), P(x1, y1, z0), P(x1, y1, z1), P(x1, y0, z1)], (1, 0, 0)),
            '-z': ([P(x0, y0, z0), P(x0, y1, z0), P(x1, y1, z0), P(x1, y0, z0)], (0, 0, -1)),
            '+z': ([P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1)], (0, 0, 1)),
        }
        for k, (pts, n) in faces.items():
            if k in skip:
                continue
            self.face(pts, (mats or {}).get(k, mat), normal=n)

    def boxc(self, cx, cy, z0, sx, sy, z1, mat, skip=(), mats=None):
        """Box from centre x/y, sizes sx/sy, z range."""
        self.box(cx - sx / 2, cy - sy / 2, z0, cx + sx / 2, cy + sy / 2, z1, mat, skip, mats)

    def hexa(self, bot, top, mat, skip_bottom=False, skip_top=False, mats=None):
        """General 8-corner convex solid: bot/top = 4 corresponding points each (any order around)."""
        bot = [V(p) for p in bot]
        top = [V(p) for p in top]
        c = (sum(bot, Vector()) + sum(top, Vector())) / 8
        mats = mats or {}
        if not skip_bottom:
            self.face(bot, mats.get('bottom', mat), center=c)
        if not skip_top:
            self.face(top, mats.get('top', mat), center=c)
        for i in range(4):
            j = (i + 1) % 4
            self.face([bot[i], bot[j], top[j], top[i]], mats.get('side', mat), center=c)

    def chamfer_box(self, x0, y0, z0, x1, y1, z1, mat, ch=0.03, top_mat=None, skip_bottom=True):
        """Box with chamfered top edges (stone blocks / slabs). ~20 tris."""
        ch = min(ch, (x1 - x0) / 3, (y1 - y0) / 3, (z1 - z0) / 2)
        t = z1
        tm = top_mat or mat
        b = [V(x0, y0, z0), V(x1, y0, z0), V(x1, y1, z0), V(x0, y1, z0)]
        m = [V(x0, y0, t - ch), V(x1, y0, t - ch), V(x1, y1, t - ch), V(x0, y1, t - ch)]
        tp = [V(x0 + ch, y0 + ch, t), V(x1 - ch, y0 + ch, t), V(x1 - ch, y1 - ch, t), V(x0 + ch, y1 - ch, t)]
        c = V((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
        if not skip_bottom:
            self.face(b, mat, normal=(0, 0, -1))
        self.face(tp, tm, normal=(0, 0, 1))
        for i in range(4):
            j = (i + 1) % 4
            self.face([b[i], b[j], m[j], m[i]], mat, center=c)
            self.face([m[i], m[j], tp[j], tp[i]], tm, center=c)

    def prism(self, poly, z0, z1, mat, top_mat=None, bottom=True, top=True, side_mat=None):
        """Vertical extrusion of a 2D polygon."""
        poly = ccw([tuple(p[:2]) for p in poly])
        n = len(poly)
        for i in range(n):
            a = poly[i]
            b = poly[(i + 1) % n]
            dx, dy = b[0] - a[0], b[1] - a[1]
            self.face([V(a[0], a[1], z0), V(b[0], b[1], z0), V(b[0], b[1], z1), V(a[0], a[1], z1)],
                      side_mat or mat, normal=(dy, -dx, 0))
        if top:
            self.face_holes([V(p[0], p[1], z1) for p in poly], [], (0, 0, 1), top_mat or mat)
        if bottom:
            self.face_holes([V(p[0], p[1], z0) for p in poly], [], (0, 0, -1), mat)

    def revolve(self, profile, seg, mat, center=(0, 0, 0), lobe=None, phase=0.0, matfn=None,
                sx=1.0, sy=1.0):
        """Surface of revolution. profile = [(r, z), ...] from bottom to top along the OUTER surface.
        r == 0 at an end closes the surface with a fan. lobe(theta) scales radius."""
        cx, cy, cz = center
        rings = []
        for (r, z) in profile:
            if r <= 1e-9:
                rings.append([V(cx, cy, cz + z)])
                continue
            ring = []
            for k in range(seg):
                th = phase + TAU * k / seg
                f = lobe(th) if lobe else 1.0
                ring.append(V(cx + r * f * math.cos(th) * sx, cy + r * f * math.sin(th) * sy, cz + z))
            rings.append(ring)
        for i in range(len(rings) - 1):
            A, B = rings[i], rings[i + 1]
            m = matfn(i, profile[i], profile[i + 1]) if matfn else mat
            if len(A) == 1 and len(B) == 1:
                continue
            for k in range(seg):
                k1 = (k + 1) % seg
                if len(A) == 1:
                    pts = [A[0], B[k], B[k1]]
                elif len(B) == 1:
                    pts = [A[k], A[k1], B[0]]
                else:
                    pts = [A[k], A[k1], B[k1], B[k]]
                n = newell(pts)
                if n.length < 1e-12:
                    continue
                self._add([p.copy() for p in pts], m)

    def cylinder(self, cx, cy, z0, z1, r, seg, mat, caps=True, r_top=None):
        rt = r if r_top is None else r_top
        prof = ([(0, z0)] if caps else []) + [(r, z0), (rt, z1)] + ([(0, z1)] if caps else [])
        self.revolve(prof, seg, mat, center=(cx, cy, 0))

    def rod(self, a, b, r, mat, seg=6):
        """Cylinder between two points."""
        a, b = V(a), V(b)
        d = b - a
        L = d.length
        if L < 1e-6:
            return
        sub = MB()
        sub.cylinder(0, 0, 0, L, r, seg, mat)
        q = Vector((0, 0, 1)).rotation_difference(d.normalized())
        M = Matrix.Translation(a) @ q.to_matrix().to_4x4()
        self.add(sub, M)

    def beam(self, a, b, w, h, mat):
        """Rectangular beam between two points (w horizontal, h vertical-ish)."""
        a, b = V(a), V(b)
        d = (b - a)
        L = d.length
        if L < 1e-6:
            return
        sub = MB()
        sub.box(0, -w / 2, -h / 2, L, w / 2, h / 2, mat)
        dn = d.normalized()
        up = Vector((0, 0, 1))
        if abs(dn.dot(up)) > 0.99:
            up = Vector((1, 0, 0))
        y = up.cross(dn).normalized()
        z = dn.cross(y).normalized()
        R = Matrix((dn, y, z)).transposed().to_4x4()
        self.add(sub, Matrix.Translation(a) @ R)

    # ------------------------------------------------------------ sweeps
    def sweep_path(self, path, profile, mat, closed=True, caps=True, z0=0.0):
        """Sweep a profile [(d, h)] along a 2D path (CCW if closed); d = outward offset, h = height.
        Profile goes bottom->top along the visible outer surface."""
        path = [tuple(p[:2]) for p in path]
        if closed:
            path = ccw(path)
        n = len(path)

        def edge_n(i):
            a = path[i]
            b = path[(i + 1) % n]
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dy) or 1.0
            return (dy / L, -dx / L)

        miters = []
        for i in range(n):
            if closed:
                n1 = edge_n((i - 1) % n)
                n2 = edge_n(i)
            else:
                n1 = edge_n(max(i - 1, 0)) if i > 0 else edge_n(0)
                n2 = edge_n(min(i, n - 2))
            sx, sy = n1[0] + n2[0], n1[1] + n2[1]
            dot = 1 + n1[0] * n2[0] + n1[1] * n2[1]
            if dot < 1e-3:
                dot = 1e-3
            miters.append((sx / dot, sy / dot))
        rings = []
        for (d, h) in profile:
            rings.append([V(path[i][0] + d * miters[i][0], path[i][1] + d * miters[i][1], z0 + h) for i in range(n)])
        segs = n if closed else n - 1
        for j in range(len(rings) - 1):
            A, B = rings[j], rings[j + 1]
            for i in range(segs):
                i1 = (i + 1) % n
                pts = [A[i], A[i1], B[i1], B[i]]
                if newell(pts).length < 1e-12:
                    continue
                self._add([p.copy() for p in pts], mat)
        if not closed and caps:
            for end, sgn in ((0, -1), (n - 1, 1)):
                a = path[0] if end == 0 else path[-1]
                b = path[1] if end == 0 else path[-2]
                dx, dy = (a[0] - b[0]), (a[1] - b[1])
                L = math.hypot(dx, dy) or 1
                pts = [rings[j][end] for j in range(len(rings))]
                # close along wall line (d = 0) implicitly: first/last profile pts assumed d=0
                if len(pts) >= 3:
                    self.face_holes(pts, [], (dx / L, dy / L, 0), mat)

    def sweep_x(self, x0, x1, y0, profile, mat, caps=True, z0=0.0):
        """Straight sweep along +X at wall plane y0, profile d towards -Y."""
        self.sweep_path([(x0, y0), (x1, y0)], profile, mat, closed=False, caps=caps, z0=z0)

    def ring_rect(self, x0, y0, x1, y1, profile, mat, z0=0.0):
        self.sweep_path([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], profile, mat, closed=True, z0=z0)


# ---------------------------------------------------------------- helpers
def T(x=0.0, y=0.0, z=0.0):
    return Matrix.Translation((x, y, z))


def Rz(deg):
    return Matrix.Rotation(math.radians(deg), 4, 'Z')


def Rx(deg):
    return Matrix.Rotation(math.radians(deg), 4, 'X')


def Ry(deg):
    return Matrix.Rotation(math.radians(deg), 4, 'Y')


def S(x, y=None, z=None):
    y = x if y is None else y
    z = x if z is None else z
    return Matrix.Diagonal((x, y, z, 1.0))


def regular_poly(n, r, cx=0.0, cy=0.0, phase=0.0):
    return [(cx + r * math.cos(phase + TAU * i / n), cy + r * math.sin(phase + TAU * i / n)) for i in range(n)]


def lerp(a, b, t):
    return a + (b - a) * t
