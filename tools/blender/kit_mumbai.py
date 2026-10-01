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
from kit_core import MB, T, Rz, lerp


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


def register(add):
    B = 'origin = bottom-centre of the FRONT facade at street level (Z=0); facade faces -Y'
    for (name, seed, W, D, fl, style) in TOWERS:
        add(name, 'building_mumbai', (lambda seed=seed, W=W, D=D, fl=fl, style=style: (highrise(seed, W, D, fl, style), [])), B,
            '%.0f x %.0f m, %d storey Mumbai %s tower (skyline backdrop).' % (W, D, fl, style))
    add('Road_Zebra_14m', 'props', zebra, 'origin = road centre; stripes along X, crossing spans Y +-6.6 m', 'Zebra crossing.')
    add('Rail_Platform_40m', 'props', platform, 'origin = bottom of the track-side edge, centre; platform extends to +Y (5 m)',
        'Suburban station platform with canopy, benches, board.')
    add('Pandal_Ganesh', 'props', pandal, 'origin = front-centre at ground; open side faces -Y', 'Ganesh festival pandal.')
    add('Festoon_Lights_10m', 'props', festoon, 'origin = ground below mid-span; wire along X at 4.2 m', 'Festoon bulbs across a lane.')
