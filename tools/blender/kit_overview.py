"""
kit_overview.py - compose a mini Dashashwamedh-style ghat scene from the kit recipes and render kit_overview.png.

  /snap/bin/blender -b -t 8 --python kit_overview.py -- --out ~/gta-india/assets/kit [--res 1600x900]
Uses Blender authoring space (river at -Y, steps rise to +Y, buildings on top at Z=+12, Y>=40).
"""
import sys
import os
import math
import random
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import bpy  # noqa
from mathutils import Vector, Matrix  # noqa
import kit_export as KE  # noqa
import kit_assets as KA  # noqa
from kit_core import MB  # noqa

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--out', default=os.path.expanduser('~/gta-india/assets/kit'))
ap.add_argument('--res', default='1600x900')
ap.add_argument('--cam', default='main')
a = ap.parse_args(argv)
out = os.path.expanduser(a.out)
rx, ry = [int(v) for v in a.res.split('x')]

REG = {r['name']: r for r in KA.registry()}
cache = {}


def place(name, x, y, z, yaw=0.0):
    if name not in cache:
        mb, hulls = REG[name]['fn']()
        ob = KE.build_object(name, mb)
        ob.hide_render = True
        ob.hide_viewport = True
        cache[name] = ob
    src = cache[name]
    ob = src.copy()
    ob.hide_render = False
    ob.hide_viewport = False
    bpy.context.scene.collection.objects.link(ob)
    ob.location = (x, y, z)
    ob.rotation_euler = (0, 0, math.radians(yaw))
    return ob


sc = KE.setup_scene(512)
sc.render.resolution_x, sc.render.resolution_y = rx, ry
rng = random.Random(4)

# ---------------------------------------------------------------- river
water = MB()
water.face([(-400, -400, 0), (400, -400, 0), (400, 0.2, 0), (-400, 0.2, 0)], 'KitPreviewWater', normal=(0, 0, 1))
wob = KE.build_object('Water', water)
wm = bpy.data.materials['KitPreviewWater']
bsdf = next(n for n in wm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
bsdf.inputs['Roughness'].default_value = 0.12
far = MB()
far.face([(-400, -170, 0.3), (400, -170, 0.3), (400, -400, 0.3), (-400, -400, 0.3)], 'M_MudDry', normal=(0, 0, 1))
KE.build_object('FarBank', far)
land = MB()
land.face([(-400, 39.95, 11.99), (400, 39.95, 11.99), (400, 400, 11.99), (-400, 400, 11.99)], 'M_DryGround', normal=(0, 0, 1))
KE.build_object('CityGround', land)

# ---------------------------------------------------------------- ghats
prof, rise = KA.step_profile(40.0, -3.0, 12.0, 3)
landings = [p for p in prof if p[3] == 'landing']
for x, nm in ((-30, 'GhatSteps_Straight_20m'), (-10, 'GhatSteps_Platform_20m'), (10, 'GhatSteps_Straight_20m'),
              (30, 'GhatSteps_Straight_20m')):
    place(nm, x, 0, 0)
place('GhatSteps_SideWall', -40.6, 0, 0)
place('GhatSteps_SideWall', 40.6, 0, 0)
top_z = 12.0

# ---------------------------------------------------------------- riverfront buildings (front row wall at y=41)
row1 = ['Bldg_Riverfront_04', 'Bldg_Riverfront_01', 'Bldg_Riverfront_06', 'Bldg_Riverfront_09', 'Temple_Medium',
        'Bldg_Riverfront_03', 'Bldg_Riverfront_12', 'Bldg_Riverfront_05']
widths = {'Temple_Medium': 9.0}
for n in row1:
    if n not in widths:
        for (nm, seed, W, D, fl, p) in __import__('kit_buildings').RIVERFRONT_VARIANTS():
            if nm == n:
                widths[n] = W + 0.6
gaps = 2.2
total = sum(widths[n] for n in row1) + gaps * (len(row1) - 1)
x = -total / 2
for n in row1:
    w = widths[n]
    y = 45.0 if n == 'Temple_Medium' else 41.0
    place(n, x + w / 2, y, top_z)
    x += w + gaps
# second row, higher up the slope
row2 = ['Palace_Darbhanga', 'Bldg_Riverfront_11', 'Bldg_Riverfront_02', 'Bldg_Riverfront_13', 'Bldg_Riverfront_10']
w2 = {'Palace_Darbhanga': 34.0}
for n in row2:
    if n not in w2:
        for (nm, seed, W, D, fl, p) in __import__('kit_buildings').RIVERFRONT_VARIANTS():
            if nm == n:
                w2[n] = W + 0.6
total = sum(w2[n] for n in row2) + 2.0 * (len(row2) - 1)
x = -total / 2 - 6
for n in row2:
    place(n, x + w2[n] / 2, 60.0, top_z)
    x += w2[n] + 2.0

# ---------------------------------------------------------------- props on the steps
place('Temple_Riverside', -26.0, 9.6, landings[0][2])
place('Temple_Small', 16.0, landings[1][0] + 1.5, landings[1][2])
place('Chhatri_Stone', -10.0, 16.0, next(p[2] for p in prof if p[0] <= 21.0 <= p[1]) - 0.05)
for i, L in enumerate(landings):
    for k in range(7):
        xx = -38 + k * 11.5 + rng.uniform(-2, 2) + (i % 2) * 5
        if -15 < xx < -5 and L[0] > 5 and L[0] < 22:
            continue
        if abs(xx + 26) < 4.5 and i == 0:
            continue
        if abs(xx - 16) < 3 and i == 1:
            continue
        yy = L[0] + rng.uniform(0.9, max(1.0, L[1] - L[0] - 0.9))
        place('Chhatri_Umbrella', xx, yy, L[2])
        if rng.random() < 0.6:
            place('Chowki_Platform', xx + 0.6, yy - 0.2, L[2], yaw=rng.uniform(-10, 10))
for xx in (-35, 5, 24):
    place('Flag_Pole_Saffron', xx, 38.5, top_z)
# ---------------------------------------------------------------- boats
for i in range(9):
    bx = -40 + i * 10 + rng.uniform(-2, 2)
    by = -2.5 - rng.uniform(0, 3) - (i % 3) * 3.5
    place('Boat_Wooden_Varanasi', bx, by, -0.3, yaw=rng.uniform(-12, 12) + (90 if i % 4 == 3 else 0))
for i in range(4):
    place('Boat_Wooden_Varanasi', -20 + i * 13, -30 - rng.uniform(0, 20), -0.3, yaw=rng.uniform(0, 180))

# ---------------------------------------------------------------- light + camera
sun = bpy.data.objects['KitSun']
sun.data.energy = 5.0
sun.data.color = (1.0, 0.72, 0.45)
sun.rotation_euler = (math.radians(74), 0, math.radians(-35))
w = bpy.data.worlds['KitWorld']
bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND')
bg.inputs['Strength'].default_value = 1.0
for attr, val in (('use_raytracing', True), ('taa_render_samples', 64)):
    try:
        setattr(sc.eevee, attr, val)
    except Exception:
        pass
cam = bpy.data.objects['KitCam']
cam.data.lens = 30
cam.data.clip_end = 3000
if a.cam == 'main':
    cam.location = (22.0, -62.0, 9.0)
    target = Vector((-4.0, 30.0, 12.0))
elif a.cam == 'close':
    cam.location = (-3.0, -8.0, 3.0)
    target = Vector((-14.0, 30.0, 16.0))
    cam.data.lens = 35
else:
    cam.location = (18.0, 20.0, 16.0)
    target = Vector((6.0, 45.0, 22.0))
    cam.data.lens = 28
d = target - cam.location
cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
g = bpy.data.objects.get('KitGround')
if g:
    g.hide_render = True
sc.render.filepath = os.path.join(out, 'kit_overview.png' if a.cam == 'main' else 'kit_overview_%s.png' % a.cam)
bpy.ops.render.render(write_still=True)
print('OVERVIEW', sc.render.filepath)
