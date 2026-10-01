"""Trial scene kit: the single Dharavi lane from the reference screenshot.
Vivid blue one-storey row houses with grey asbestos roofs sloping down over a ~4 m lane, raised concrete
otas, curtain / wooden doors, barred windows, clothes on lines under the eaves; big laundry lines strung
high across the lane; a brick two-storey behind; the end house facing down the lane.
Reuses the Dharavi kit's shanty / laundry builders.
"""
import random
from kit_core import MB, V, T, Rz
import kit_dharavi as KD

# (name, seed, W, D, params) - the left / right rows are placed side by side in UE, fronts on the lane
TRIAL_HOUSES = [
    ('Trial_House_01', 5101, 3.9, 4.6, dict(mat='M_PlasterBlueVivid', h=2.6, roof='asb', door='curtain', windows=1, eave_line=True,
                                            slope='front', ota=0.6, tarp_p=0.0, side='M_PlasterBlueVivid', door_awning=False)),
    ('Trial_House_02', 5102, 4.3, 4.6, dict(mat='M_PlasterBlueVivid', h=2.55, roof='asb', door='closed', windows=1, eave_line=True,
                                            slope='front', ota=0.55, tarp_p=0.0, side='M_PlasterBlueVivid')),
    ('Trial_House_03', 5103, 3.6, 4.6, dict(mat='M_PlasterBlueVivid', h=2.7, roof='asb', door='open', windows=1, eave_line=False,
                                            slope='front', ota=0.65, tarp_p=0.0, side='M_PlasterBlueVivid', door_awning=False)),
    ('Trial_House_04', 5104, 4.1, 4.6, dict(mat='M_PlasterBlueVivid', h=2.6, roof='asb', door='curtain', windows=2, eave_line=True,
                                            slope='front', ota=0.5, tarp_p=0.0, side='M_PlasterBlueVivid')),
    ('Trial_House_05', 5105, 3.8, 4.6, dict(mat='M_PlasterBlueVivid', h=2.65, roof='asb', door='closed', windows=1, eave_line=True,
                                            slope='front', ota=0.6, tarp_p=0.0, side='M_PlasterBlueVivid', door_awning=False)),
    ('Trial_House_06', 5106, 4.4, 4.6, dict(mat='M_PlasterCream', h=2.75, roof='asb', door='curtain', windows=1, eave_line=True,
                                            slope='front', ota=0.6, tarp_p=0.0, side='M_PlasterCream', trim='M_PlasterBlueVivid')),
    ('Trial_House_07', 5107, 3.7, 4.6, dict(mat='M_PlasterBlueVivid', h=2.55, roof='mix', door='open', windows=1, eave_line=True,
                                            slope='front', ota=0.55, tarp_p=0.0, side='M_PlasterBlueVivid')),
    ('Trial_House_08', 5108, 4.0, 4.6, dict(mat='M_PlasterBlueVivid', h=2.7, roof='asb', door='closed', windows=2, eave_line=False,
                                            slope='front', ota=0.6, tarp_p=0.0, side='M_PlasterBlueVivid')),
    ('Trial_House_09', 5109, 4.6, 5.0, dict(mat='M_PlasterBlueVivid', h=2.8, roof='asb', door='curtain', windows=2, eave_line=True,
                                            slope='front', ota=0.7, tarp_p=0.0, side='M_PlasterBlueVivid')),
    ('Trial_House_10', 5110, 3.5, 4.6, dict(mat='M_PlasterTeal', h=2.6, roof='asb', door='closed', windows=1, eave_line=True,
                                            slope='front', ota=0.55, tarp_p=0.0, side='M_PlasterTeal')),
]


def cross_laundry(seed, span, z_a, z_b, n):
    """Laundry strung across the lane from wall to wall (rope along X here; rotate 90 in UE)."""
    rng = random.Random(seed)
    mb = MB()
    KD.laundry_on_line(mb, rng, -span / 2, span / 2, z_a, z_b, 0.0, 0.28, n,
                       kinds=['shirt', 'shirt', 'pants', 'pants', 'towel', 'kurta', 'shirt', 'dupatta'], maxlen=1.3)
    # hooks / nails at both ends
    for x, z in ((-span / 2, z_a), (span / 2, z_b)):
        mb.boxc(x, 0, z - 0.04, 0.05, 0.05, z + 0.04, 'M_MetalRust')
    return mb


def wall_laundry(seed, L, z, n):
    """A clothesline along a wall (just under an eave), rope along X, hanging in front of the wall (-Y)."""
    rng = random.Random(seed)
    mb = MB()
    KD.laundry_on_line(mb, rng, -L / 2, L / 2, z, z - 0.03, -0.18, 0.1, n, kinds=['shirt', 'towel', 'kurta', 'shirt', 'dupatta', 'pants'],
                       maxlen=1.0)
    return mb


def slippers(seed=5150):
    """A pair of rubber chappals left by a door."""
    rng = random.Random(seed)
    mb = MB()
    for k, (x, y, a) in enumerate(((0.0, 0.0, 8), (0.13, 0.04, -12))):
        sub = MB()
        sub.chamfer_box(-0.05, -0.13, 0.0, 0.05, 0.13, 0.018, rng.choice(['M_PlasticRed', 'M_PlasticBlue']), ch=0.006)
        sub.box(-0.004, -0.06, 0.018, 0.004, 0.0, 0.035, 'M_Rubber')
        mb.add(sub, T(x, y, 0) @ Rz(a))
    return mb, []


def register(add):
    for (name, seed, W, D, p) in TRIAL_HOUSES:
        add(name, 'building_trial', (lambda seed=seed, W=W, D=D, p=p: (KD.shanty(seed, W, D, p), [])),
            'origin = bottom-centre of the FRONT facade at lane level; facade faces -Y', '%.1f m Trial lane row house' % W)
    for i, (span, za, zb, n) in enumerate(((5.6, 4.6, 4.2, 9), (5.2, 3.9, 4.3, 8), (6.0, 4.0, 3.7, 10), (5.4, 3.6, 3.8, 7))):
        add('Trial_Laundry_Cross_%02d' % (i + 1), 'props', (lambda i=i, span=span, za=za, zb=zb, n=n: (cross_laundry(5200 + i, span, za, zb, n), [])),
            'origin = ground below mid-span; rope along X at the given heights', 'Laundry across the lane.')
    for i, (L, z, n) in enumerate(((3.6, 2.35, 5), (4.2, 2.3, 6), (3.0, 2.4, 4))):
        add('Trial_Laundry_Wall_%02d' % (i + 1), 'props', (lambda i=i, L=L, z=z, n=n: (wall_laundry(5300 + i, L, z, n), [])),
            'origin = ground at the wall, rope along X, clothes hang 0.18 m in front (-Y)', 'Clothesline along a wall.')
    add('Trial_Slippers', 'props', slippers, 'origin = ground', 'Pair of chappals.')
