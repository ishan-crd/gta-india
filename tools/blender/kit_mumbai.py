"""Mumbai map kit: the pieces the Dharavi / Trial kits don't cover.
  * Tower_Highrise_01..08 - plain concrete SRA / housing-society towers and a few glass offices for the
    skyline behind the slum (cheap: window bands, slab ledges, a few balconies, rooftop tanks);
  * Road_Zebra_14m - a zebra crossing across a 14 m road;
  * Rail_Platform_40m - a suburban station platform with a tin canopy on steel columns, yellow edge line,
    benches and a station board;
  * Pandal_Ganesh - a small festival pandal (bamboo frame, saffron / red drapes, raised plinth for the idol);
  * Festoon_Lights_10m - a sagging string of coloured bulbs strung across a lane.
"""
import random
from kit_core import MB, T, Rz, V, lerp


# ------------------------------------------------------------------------------------- high-rises
def highrise(seed, W, D, floors, style):
    """Origin bottom-centre of the front facade (faces -Y); body extends to +Y."""
    rng = random.Random(seed)
    mb = MB()
    fh = 3.1
    H = floors * fh + 1.2
    if style == 'glass':
        body, band, ledge = 'M_Glass', 'M_Glass', 'M_Concrete'
    else:
        body = rng.choice(['M_PlasterCream', 'M_PlasterWhite', 'M_PlasterWorn', 'M_ConcreteDirty', 'M_PlasterYellow', 'M_PlasterPeeling'])
        band, ledge = 'M_WindowDark', 'M_Concrete'
    mb.box(-W / 2, 0, 0, W / 2, D, H, body)
    bay = 3.0
    nb = max(2, int(W / bay))
    bw = W / nb
    for f in range(floors):
        z = 0.9 + f * fh
        # slab ledge round the front and sides
        mb.box(-W / 2 - 0.08, -0.12, z - 0.12, W / 2 + 0.08, 0.0, z, ledge)
        if style == 'glass':
            continue
        for i in range(nb):
            cx = -W / 2 + (i + 0.5) * bw
            ww = bw * rng.uniform(0.6, 0.75)
            mb.box(cx - ww / 2, -0.03, z + 0.6, cx + ww / 2, 0.0, z + 2.3, band)
            # side windows
        if rng.random() < 0.5:
            for sx in (-W / 2, W / 2):
                for k in range(max(1, int(D / 4))):
                    cy = 2.0 + k * 4.0
                    if cy < D - 1:
                        a = sx - 0.03 if sx > 0 else sx
                        mb.box(min(a, a + 0.03), cy - 0.6, z + 0.8, max(a, a + 0.03), cy + 0.6, z + 2.2, band)
        # a few balconies with railings / AC boxes on the front
        if f > 0 and rng.random() < 0.6:
            i = rng.randrange(nb)
            cx = -W / 2 + (i + 0.5) * bw
            mb.box(cx - bw * 0.4, -0.9, z, cx + bw * 0.4, 0.0, z + 0.12, ledge)
            mb.box(cx - bw * 0.4, -0.92, z + 0.12, cx + bw * 0.4, -0.86, z + 1.0, 'M_Steel')
        if f > 0 and rng.random() < 0.4:
            cx = -W / 2 + (rng.randrange(nb) + 0.85) * bw
            mb.box(cx - 0.4, -0.45, z + 2.25, cx + 0.4, -0.03, z + 2.8, 'M_PlasterWhite')
    if style == 'glass':
        # vertical mullions so the glass reads as a facade
        for i in range(nb + 1):
            x = -W / 2 + i * bw
            mb.box(x - 0.12, -0.15, 0, x + 0.12, 0.0, H, 'M_Concrete')
    # parapet, lift room, water tanks, dish
    mb.box(-W / 2, -0.15, H, W / 2, D, H + 1.0, ledge, skip=('-z',))
    mb.box(-2.0, D * 0.4, H, 2.0, D * 0.4 + 3.5, H + 3.2, body)
    for k in range(rng.randint(2, 4)):
        x, y = rng.uniform(-W / 2 + 1.5, W / 2 - 1.5), rng.uniform(1.5, D - 1.5)
        mb.cylinder(x, y, H, H + 1.6, 0.7, 10, 'M_WindowDark')
    return mb


TOWERS = [  # name, seed, W, D, floors, style
    ('Tower_Highrise_01', 7101, 18.0, 14.0, 16, 'plain'),
    ('Tower_Highrise_02', 7102, 22.0, 16.0, 22, 'plain'),
    ('Tower_Highrise_03', 7103, 15.0, 15.0, 28, 'plain'),
    ('Tower_Highrise_04', 7104, 26.0, 18.0, 12, 'plain'),
    ('Tower_Highrise_05', 7105, 20.0, 20.0, 34, 'glass'),
    ('Tower_Highrise_06', 7106, 16.0, 16.0, 40, 'glass'),
    ('Tower_Highrise_07', 7107, 24.0, 14.0, 18, 'plain'),
    ('Tower_Highrise_08', 7108, 18.0, 18.0, 25, 'plain'),
]


# ------------------------------------------------------------------------------------- street pieces
def zebra():
    """Stripes run along X (with the traffic), repeated across the road (Y); origin = road centre."""
    mb = MB()
    y = -6.6
    while y < 6.6:
        mb.box(-1.6, y, 0.0, 1.6, y + 0.5, 0.012, 'M_Whitewash')
        y += 1.0
    # stop lines either side
    mb.box(-2.4, -6.8, 0.0, -2.2, 6.8, 0.012, 'M_Whitewash')
    mb.box(2.2, -6.8, 0.0, 2.4, 6.8, 0.012, 'M_Whitewash')
    return mb, []


def platform():
    """40 m along X, 5 m deep (Y 0..5), 0.9 m high; the track side is -Y (yellow edge line there)."""
    rng = random.Random(7300)
    mb = MB()
    L, Dp, Hp = 40.0, 5.0, 0.9
    mb.box(-L / 2, 0, 0, L / 2, Dp, Hp, 'M_Concrete')
    mb.box(-L / 2, 0.0, Hp, L / 2, 0.45, Hp + 0.012, 'M_PlasticYellow')
    mb.box(-L / 2, 0.45, Hp, L / 2, 0.75, Hp + 0.01, 'M_Pavement')
    # ramps at both ends
    for sx in (-1, 1):
        x0 = sx * L / 2
        mb.hexa([(x0, 0.6, 0), (x0, Dp, 0), (x0 + sx * 4.0, Dp, 0), (x0 + sx * 4.0, 0.6, 0)],
                [(x0, 0.6, Hp), (x0, Dp, Hp), (x0 + sx * 4.0, Dp, 0.02), (x0 + sx * 4.0, 0.6, 0.02)], 'M_Concrete')
    # columns + tin canopy
    for i in range(9):
        x = -L / 2 + 2.5 + i * 4.375
        mb.boxc(x, Dp * 0.55, Hp, 0.22, 0.22, Hp + 3.6, 'M_Steel')
    mb.hexa([(-L / 2 + 1, -0.2, Hp + 3.9), (L / 2 - 1, -0.2, Hp + 3.9), (L / 2 - 1, Dp + 0.3, Hp + 3.4), (-L / 2 + 1, Dp + 0.3, Hp + 3.4)],
            [(-L / 2 + 1, -0.2, Hp + 3.98), (L / 2 - 1, -0.2, Hp + 3.98), (L / 2 - 1, Dp + 0.3, Hp + 3.48), (-L / 2 + 1, Dp + 0.3, Hp + 3.48)],
            'M_CorrugatedGalv')
    mb.box(-L / 2 + 1, Dp * 0.55 - 0.1, Hp + 3.5, L / 2 - 1, Dp * 0.55 + 0.1, Hp + 3.7, 'M_Steel')
    # benches
    for i in range(4):
        x = -14 + i * 9.0 + rng.uniform(-1, 1)
        mb.box(x - 0.9, Dp * 0.7, Hp + 0.42, x + 0.9, Dp * 0.7 + 0.4, Hp + 0.48, 'M_Steel')
        for lx in (x - 0.8, x + 0.8):
            mb.box(lx - 0.03, Dp * 0.7, Hp, lx + 0.03, Dp * 0.7 + 0.4, Hp + 0.42, 'M_Steel')
    # station board hanging from the canopy
    mb.box(-1.6, Dp * 0.55 - 0.04, Hp + 2.7, 1.6, Dp * 0.55 + 0.04, Hp + 3.3, 'M_PlasticYellow')
    mb.box(-1.5, Dp * 0.55 - 0.05, Hp + 2.78, 1.5, Dp * 0.55 + 0.05, Hp + 3.22, 'M_WindowDark')
    # back wall / fence
    mb.box(-L / 2, Dp - 0.12, Hp, L / 2, Dp, Hp + 1.2, 'M_PlasterWorn')
    return mb, []


def pandal():
    """4 x 4 m festival pandal: bamboo posts, cloth roof and side drapes; idol plinth at the back centre.
    Origin = front-centre at ground; the open front faces -Y."""
    mb = MB()
    W, D, H = 4.4, 4.0, 3.4
    for x in (-W / 2, W / 2):
        for y in (0.0, D):
            mb.cylinder(x, y, 0, H, 0.06, 6, 'M_WoodPlanks')
    mb.box(-W / 2 - 0.1, -0.1, H, W / 2 + 0.1, D + 0.1, H + 0.05, 'M_Saffron')
    # gathered valance at the front
    for i in range(11):
        x = -W / 2 + i * W / 10
        mb.box(x - 0.2, -0.12, H - 0.45 - (0.12 if i % 2 else 0), x + 0.2, -0.08, H, 'M_LaundryRed' if i % 2 else 'M_Saffron')
    # back / side drapes
    mb.box(-W / 2, D - 0.05, 0, W / 2, D, H, 'M_LaundryRed')
    for x in (-W / 2, W / 2 - 0.05):
        mb.box(x, 0.6, 0, x + 0.05, D, H, 'M_Saffron')
    # plinth for the idol + marigold edge
    mb.box(-1.2, D - 1.9, 0, 1.2, D - 0.2, 0.7, 'M_LaundryRed')
    mb.box(-1.25, D - 1.95, 0.6, 1.25, D - 1.88, 0.72, 'M_LaundryOrange')
    return mb, []


def festoon(L=10.0, seed=7400):
    """A sagging wire across a lane with coloured bulbs (wire along X, ends at Z 4.2)."""
    rng = random.Random(seed)
    mb = MB()
    n = 40
    sag = 0.6
    mats = ['M_PlasticRed', 'M_PlasticYellow', 'M_PlasticBlue', 'M_LaundryGreen', 'M_LaundryPink', 'M_LaundryOrange']
    prev = None
    for i in range(n + 1):
        t = i / n
        x = lerp(-L / 2, L / 2, t)
        z = 4.2 - sag * 4 * t * (1 - t)
        if prev:
            mb.box(prev[0], -0.008, prev[1] - 0.008, x, 0.008, max(prev[1], z) + 0.008, 'M_Rubber')
        if 0 < i < n:
            mb.boxc(x, 0, z - 0.11, 0.07, 0.07, z - 0.02, rng.choice(mats))
        prev = (x, z)
    return mb, []


# ===================================================================================== Marine Drive
# Measured from reference photos (Queen's Necklace, Back Bay, faces WSW): a broad flat-topped sea-wall
# parapet ~1.7 m wide standing ~0.5 m above the walkway, a tan stone strip, ~6 m of grey paving, a kerb,
# then the six-lane Netaji Subhash Chandra Bose Road; concrete tetrapods (~1.8 m) piled against the
# sea face; five-six storey Art Deco apartments with curved corners, eyebrow sunshades and long
# balconies across the road; the Air India tower and Nariman Point slabs at the south end.
from mathutils import Matrix, Vector as _V


def _leg(mb, d, length, r0, r1, mat, seg=10):
    """A truncated cone from the origin along direction d."""
    sub = MB()
    sub.cylinder(0, 0, 0.0, length, r0, seg, mat, caps=True, r_top=r1)
    q = _V((0, 0, 1)).rotation_difference(_V(d).normalized())
    mb.add(sub, q.to_matrix().to_4x4())


def tetrapod():
    """Four legs at tetrahedral angles; origin = centre of the hub; ~1.9 m across."""
    mb = MB()
    a = 1.0 / 3.0
    dirs = [(0, 0, 1), (0.9428, 0, -a), (-0.4714, 0.8165, -a), (-0.4714, -0.8165, -a)]
    for d in dirs:
        _leg(mb, d, 1.15, 0.36, 0.24, 'M_ConcreteDirty', seg=9)
    # hub
    mb.cylinder(0, 0, -0.3, 0.3, 0.33, 9, 'M_ConcreteDirty')
    return mb, []


def md_seawall():
    """10 m of sea wall + promenade along X. Origin = sea face of the parapet at walkway level (Z = 0);
    the sea is -Y. Parapet top Z = +0.52, sea face drops to -3.6 (water about -2.6)."""
    mb = MB()
    L = 10.0
    x0, x1 = -L / 2, L / 2
    # sea face and the parapet body
    mb.box(x0, -0.05, -3.6, x1, 1.75, 0.5, 'M_ConcreteDirty', skip=('-z',))
    # parapet top slabs (light, worn) with joints every 2.5 m
    for i in range(4):
        a, b = x0 + i * 2.5 + 0.01, x0 + (i + 1) * 2.5 - 0.01
        mb.box(a, -0.08, 0.5, b, 1.78, 0.52, 'M_Concrete')
    # tan stone strip and step down to the walkway
    mb.box(x0, 1.78, 0.0, x1, 2.3, 0.2, 'M_SandstoneOld')
    # walkway paving (grey slabs) and the road kerb
    for i in range(5):
        a, b = x0 + i * 2.0 + 0.008, x0 + (i + 1) * 2.0 - 0.008
        mb.box(a, 2.3, -0.06, b, 8.3, 0.0, 'M_Concrete')
    mb.box(x0, 8.3, -0.2, x1, 8.6, 0.05, 'M_Concrete')
    return mb, [[(x, y, z) for x in (x0, x1) for y in (-0.05, 1.78) for z in (-3.6, 0.52)],
                [(x, y, z) for x in (x0, x1) for y in (1.78, 8.6) for z in (-0.3, 0.0)]]


def md_road():
    """10 m of the six-lane road along X. Origin = near kerb face at walkway level; road surface Z = -0.15;
    lanes 3.5 m, median 1.4 m, far kerb + 4 m footpath."""
    mb = MB()
    x0, x1 = -5.0, 5.0
    half = 3 * 3.5
    yA = 0.0
    yM0, yM1 = yA + half, yA + half + 1.4
    yB = yM1 + half
    mb.box(x0, yA, -0.4, x1, yB, -0.15, 'M_Asphalt')
    # lane dashes
    for k in (1, 2):
        for side0 in (yA, yM1):
            y = side0 + k * 3.5
            for i in range(2):
                a = x0 + i * 5.0 + 0.5
                mb.box(a, y - 0.06, -0.15, a + 3.0, y + 0.06, -0.14, 'M_Whitewash')
    # edge lines
    for y in (yA + 0.3, yB - 0.3, yM0 - 0.25, yM1 + 0.25):
        mb.box(x0, y - 0.05, -0.15, x1, y + 0.05, -0.14, 'M_Whitewash')
    # median: kerbs + low hedge strip
    mb.box(x0, yM0, -0.15, x1, yM1, 0.15, 'M_Concrete')
    mb.box(x0, yM0 + 0.2, 0.15, x1, yM1 - 0.2, 0.55, 'M_VegGreen')
    # far kerb and footpath
    mb.box(x0, yB, -0.2, x1, yB + 0.3, 0.05, 'M_Concrete')
    mb.box(x0, yB + 0.3, -0.1, x1, yB + 4.3, 0.0, 'M_Concrete')
    return mb, [[(x, y, z) for x in (x0, x1) for y in (yA, yB + 4.3) for z in (-0.5, -0.15)]]


def md_lamp():
    """Promenade street lamp (the Queen's Necklace): 9 m pole on the road side of the walkway, the arm
    reaching over the walkway (-Y). Origin = pole base."""
    mb = MB()
    mb.cylinder(0, 0, 0, 0.5, 0.16, 10, 'M_Steel')
    mb.cylinder(0, 0, 0.5, 8.6, 0.09, 8, 'M_Steel', r_top=0.06)
    mb.box(-0.04, -1.6, 8.5, 0.04, 0.0, 8.6, 'M_Steel')
    mb.box(-0.18, -1.95, 8.32, 0.18, -1.45, 8.5, 'M_Steel')
    mb.box(-0.14, -1.9, 8.28, 0.14, -1.5, 8.32, 'M_LaundryYellow')
    return mb, []


def _rounded_corner(mb, cx, cy, r, z0, z1, a0, a1, mat, seg=8):
    import math
    pts = [(cx + r * math.cos(a0 + (a1 - a0) * i / seg), cy + r * math.sin(a0 + (a1 - a0) * i / seg)) for i in range(seg + 1)]
    for (ax, ay), (bx, by) in zip(pts[:-1], pts[1:]):
        mb.face([V(ax, ay, z0), V(bx, by, z0), V(bx, by, z1), V(ax, ay, z1)], mat, center=V(cx, cy, (z0 + z1) / 2))


def art_deco(seed, W, D, floors, mat):
    """Marine Drive Art Deco apartment: front faces -Y (the sea). Curved corner on the +X side, eyebrow
    sunshades over every window band, long balconies with rounded ends, a stepped crown over the stair
    tower, name plaque, compound wall in front."""
    import math
    rng = random.Random(seed)
    mb = MB()
    fh = 3.2
    H = floors * fh + 0.6
    r = 3.2
    x0, x1 = -W / 2, W / 2
    trim = rng.choice(['M_PlasterWhite', 'M_Whitewash', 'M_PlasterCream'])
    # body with a rounded front corner at +X
    mb.box(x0, 0, 0, x1 - r, D, H, mat)
    mb.box(x1 - r, r, 0, x1, D, H, mat)
    mb.box(x1 - r, 0, 0, x1 - 0.001, r, H, mat, skip=('-y', '+x'))
    _rounded_corner(mb, x1 - r, r, r, 0, H, -math.pi / 2, 0, mat)
    # window bands + eyebrows on each floor (front)
    bays = max(3, int((W - r) / 3.0))
    bw = (W - r) / bays
    for f in range(1, floors):
        z = f * fh
        for i in range(bays):
            cx = x0 + (i + 0.5) * bw
            mb.box(cx - bw * 0.32, -0.02, z + 0.9, cx + bw * 0.32, 0.0, z + 2.4, 'M_WindowDark')
        # eyebrow sunshade running the whole front and round the corner
        mb.box(x0 - 0.05, -0.55, z + 2.55, x1 - r, 0.0, z + 2.65, trim)
        _rounded_corner(mb, x1 - r, r, r + 0.55, z + 2.55, z + 2.65, -math.pi / 2, 0, trim)
        # curved-corner windows
        for k in range(3):
            a = -math.pi / 2 + (k + 0.5) * (math.pi / 2) / 3
            px, py = x1 - r + (r + 0.01) * math.cos(a), r + (r + 0.01) * math.sin(a)
            mb.boxc(px, py, z + 0.9, 0.9, 0.9, z + 2.4, 'M_WindowDark')
        # long balcony with a rounded end on alternate floors
        if f % 2 == 1:
            mb.box(x0 + bw * 0.5, -1.25, z, x0 + bw * (bays - 0.6), 0.0, z + 0.15, trim)
            mb.box(x0 + bw * 0.5, -1.28, z + 0.15, x0 + bw * (bays - 0.6), -1.2, z + 1.0, trim)
    # horizontal speed lines at the ground floor and a plinth
    mb.box(x0, -0.06, 0.0, x1 - r, 0.0, 0.9, 'M_SandstoneOld')
    for k in range(3):
        mb.box(x0, -0.05, 1.3 + k * 0.35, x1 - r, 0.0, 1.38 + k * 0.35, trim)
    # stepped crown on a central stair tower
    cx = x0 + W * 0.35
    for k, (w, h) in enumerate(((3.6, 2.2), (2.6, 1.6), (1.6, 1.4))):
        z = H + sum(hh for _, hh in ((3.6, 2.2), (2.6, 1.6), (1.6, 1.4))[:k])
        mb.box(cx - w / 2, -0.1, z, cx + w / 2, 2.5, z + h, trim)
    mb.box(cx - 0.12, -0.15, H, cx + 0.12, -0.1, H + 4.8, 'M_PlasterYellow')
    # parapet and water tanks
    mb.box(x0, 0, H, x1 - r, 0.3, H + 0.9, trim)
    for k in range(2):
        mb.cylinder(x0 + 3 + k * 4, D * 0.6, H, H + 1.7, 0.75, 10, 'M_WindowDark')
    # compound wall + gate pillars in front (on the footpath line)
    mb.box(x0, -4.2, 0, x1, -4.0, 1.1, mat)
    for gx in (x0 + W * 0.45, x0 + W * 0.45 + 3.5):
        mb.boxc(gx, -4.1, 0, 0.5, 0.5, 1.8, trim)
    return mb


ART_DECO = [  # name, seed, W, D, floors, wall
    ('ArtDeco_Apt_01', 7501, 24.0, 16.0, 6, 'M_PlasterCream'),
    ('ArtDeco_Apt_02', 7502, 20.0, 15.0, 5, 'M_PlasterYellow'),
    ('ArtDeco_Apt_03', 7503, 26.0, 16.0, 6, 'M_PlasterWhite'),
    ('ArtDeco_Apt_04', 7504, 22.0, 14.0, 5, 'M_PlasterPainted'),
    ('ArtDeco_Apt_05', 7505, 18.0, 15.0, 6, 'M_PlasterOchre'),
]


def air_india():
    """The Air India building at Nariman Point: a 23-storey white slab (~87 m) with dense vertical fins
    and the red sign on top. Origin = bottom-centre of the long (sea-facing) side; faces -Y."""
    mb = MB()
    W, D, H = 46.0, 20.0, 86.0
    mb.box(-W / 2, 0, 0, W / 2, D, H, 'M_WindowDark')
    n = 46
    for i in range(n + 1):
        x = -W / 2 + i * W / n
        mb.box(x - 0.18, -0.35, 4.0, x + 0.18, 0.0, H - 2.0, 'M_PlasterWhite')
    for sx in (-W / 2, W / 2):
        mb.box(sx - (0.4 if sx > 0 else 0.0) + (0.0 if sx > 0 else -0.0), -0.4, 0, sx + (0.0 if sx > 0 else 0.4), D + 0.4, H, 'M_PlasterWhite')
    mb.box(-W / 2, -0.5, 0, W / 2, 0.0, 4.0, 'M_PlasterWhite')
    mb.box(-W / 2, -0.5, H - 2.0, W / 2, D, H + 1.0, 'M_PlasterWhite')
    mb.box(-W * 0.3, -0.6, H + 1.0, W * 0.3, 0.0, H + 5.0, 'M_PlasticRed')
    return mb, []


def malabar_hill():
    """A broad low wooded hill (Malabar Hill across the bay): 900 x 450 m, 45 m high."""
    import math
    mb = MB()
    nx, ny = 18, 9
    pts = {}
    for i in range(nx + 1):
        for j in range(ny + 1):
            u, v = i / nx * 2 - 1, j / ny * 2 - 1
            h = max(0.0, 1 - u * u) * max(0.0, 1 - v * v)
            pts[i, j] = V(u * 450, v * 225, -3 + 48 * h ** 0.8)
    for i in range(nx):
        for j in range(ny):
            mb.face([pts[i, j], pts[i + 1, j], pts[i + 1, j + 1], pts[i, j + 1]], 'M_VegGreen', normal=V(0, 0, 1))
    return mb, []


def register(add):
    B = 'origin = bottom-centre of the FRONT facade at street level (Z=0); facade faces -Y'
    for (name, seed, W, D, fl, style) in TOWERS:
        add(name, 'building_mumbai', (lambda seed=seed, W=W, D=D, fl=fl, style=style: (highrise(seed, W, D, fl, style), [])), B,
            '%.0f x %.0f m, %d storey Mumbai %s tower (skyline backdrop).' % (W, D, fl, style))
    add('Road_Zebra_14m', 'props', zebra, 'origin = road centre; stripes along X, crossing spans Y +-6.6 m', 'Zebra crossing.')
    add('Rail_Platform_40m', 'props', platform, 'origin = bottom of the track-side edge, centre; platform extends to +Y (5 m)',
        'Suburban station platform with canopy, benches, board.')
    add('Pandal_Ganesh', 'props', pandal, 'origin = front-centre at ground; open side faces -Y', 'Ganesh festival pandal.')
    add('Tetrapod', 'props', tetrapod, 'origin = hub centre; four legs at tetrahedral angles', 'Concrete tetrapod armour unit.')
    add('MD_Seawall_10m', 'props', md_seawall, 'origin = sea face at walkway level; along X; sea is -Y',
        'Marine Drive sea wall, parapet, stone strip, paved walkway and kerb.')
    add('MD_Road_10m', 'props', md_road, 'origin = near kerb face at walkway level; along X; road extends +Y',
        'Six-lane road with median and far footpath.')
    add('MD_Lamp', 'props', md_lamp, 'origin = pole base; arm reaches -Y', 'Queen\'s Necklace street lamp.')
    for (name, seed, W, D, fl, mat) in ART_DECO:
        add(name, 'building_mumbai', (lambda seed=seed, W=W, D=D, fl=fl, mat=mat: (art_deco(seed, W, D, fl, mat), [])),
            'origin = bottom-centre of the FRONT facade (Z=0); faces -Y', '%d storey Marine Drive Art Deco apartment.' % fl)
    add('Tower_AirIndia', 'building_mumbai', air_india, 'origin = bottom-centre of the sea face; faces -Y', 'Air India building.')
    add('Hill_Malabar', 'props', malabar_hill, 'origin = centre at sea level', 'Malabar Hill across the bay.')
    add('Festoon_Lights_10m', 'props', festoon, 'origin = ground below mid-span; wire along X at 4.2 m', 'Festoon bulbs across a lane.')
