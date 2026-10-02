"""
build_kit.py - generate the Varanasi environment kit (FBX + previews + manifest part).

Usage (headless, on the Linux PC):
  /snap/bin/blender -b -t 8 --python build_kit.py -- --out ~/gta-india/assets/kit [--only A,B] [--part 0/3] [--no-preview]
  /snap/bin/blender -b --python build_kit.py -- --out ~/gta-india/assets/kit --merge     (merge manifest parts)

Deterministic: every recipe is seeded; running again reproduces identical meshes.
"""
import sys
import os
import json
import time
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bpy  # noqa: E402
import kit_export as KE  # noqa: E402
import kit_assets as KA  # noqa: E402
import kit_buildings as KB  # noqa: E402

EXPORT_SETTINGS = dict(
    operator='bpy.ops.export_scene.fbx',
    use_selection=True, object_types=['MESH'], global_scale=1.0, apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_UNITS', axis_forward='Y', axis_up='Z', bake_space_transform=False,
    mesh_smooth_type='FACE', use_triangles=True, use_tspace=False, add_leaf_bones=False, bake_anim=False,
    path_mode='STRIP', pre_export_bake='mesh data rotated 180 deg about Z (restored after export)',
)
UE_NOTES = ("FBX header axis system = Z-up / front -Y / right-handed / UnitScaleFactor 100 (cm) = UE's own FBX import axis system, "
            "so UE applies no axis conversion; UE's importer then mirrors Y (RH->LH). Combined with the baked 180 deg Z rotation the "
            "net mapping is UE(x,y,z)cm = 100*(-bx, by, bz): facades face UE -Y (river), ghat steps rise towards UE +Y, "
            "Z up, 1 m = 100 cm. The mapping is a proper rotation (no mirroring). All kit pivots are centred on X so bounds are unchanged. "
            "Import with default UE settings (Convert Scene ON, Force Front X Axis OFF, Import Uniform Scale 1.0). "
            "Note: re-importing the FBX into Blender shows the assets rotated 180 deg (facade +Y), which is expected.")


def parse():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.expanduser('~/gta-india/assets/kit'))
    ap.add_argument('--only', default='')
    ap.add_argument('--part', default='0/1')
    ap.add_argument('--no-preview', action='store_true')
    ap.add_argument('--no-export', action='store_true')
    ap.add_argument('--merge', action='store_true')
    ap.add_argument('--res', type=int, default=512)
    return ap.parse_args(argv)


def merge(out):
    parts = sorted(f for f in os.listdir(out) if f.startswith('_manifest_part_') and f.endswith('.json'))
    entries = {}
    for f in parts:
        for e in json.load(open(os.path.join(out, f))):
            entries[e['name']] = e
    order = [r['name'] for r in KA.registry()]
    assets = [entries[n] for n in order if n in entries]
    man = dict(
        kit='GTA India - Varanasi procedural environment kit',
        generator='repo/tools/blender/build_kit.py (kit_core, kit_arch, kit_buildings, kit_assets, kit_export)',
        units='metres in Blender (1 m = 100 UE cm)',
        uv='UV0 world-scale box projection, 1 UV unit = 2 m (M_Signboard faces use 0..1 per board)',
        fbx_export=EXPORT_SETTINGS,
        ue_orientation=UE_NOTES,
        collision='UCX_<Name>_NN convex hulls included in some FBX (steps ramps, gate); UE auto-collision otherwise.',
        assets=assets)
    json.dump(man, open(os.path.join(out, 'kit_manifest.json'), 'w'), indent=1)
    print('MANIFEST', len(assets), 'assets')


# Slum buildings get simple box colliders instead of their render mesh, so open doorways, gaps under
# the eaves and ladders can't trap the player: the body (facade plane Y=0 back to the rear wall, ground
# to roof) plus a low step for the raised ota in front of it.
SOLID_BUILDINGS = {'building_trial', 'building_dharavi', 'building_mumbai'}


def solid_building_hulls(st):
    (x0, y0, z0), (x1, y1, z1) = st['min'], st['max']
    x0, x1 = x0 + 0.02, x1 - 0.02

    def box(a, b, c, d, e, f):
        return [(x, y, z) for x in (a, b) for y in (c, d) for z in (e, f)]
    hulls = [box(x0, x1, 0.0, y1, max(z0, 0.0), z1)]
    if y0 < -0.1:
        hulls.append(box(x0, x1, max(y0, -0.7), 0.0, 0.0, 0.24))
    return hulls


def main():
    a = parse()
    out = os.path.expanduser(a.out)
    os.makedirs(os.path.join(out, 'previews'), exist_ok=True)
    if a.merge:
        merge(out)
        return
    reg = KA.registry()
    only = [s for s in a.only.split(',') if s]
    if only:
        reg = [r for r in reg if r['name'] in only]
    k, n = [int(x) for x in a.part.split('/')]
    reg = [r for i, r in enumerate(reg) if i % n == k]
    entries = []
    KE.setup_scene(a.res)
    for r in reg:
        t0 = time.time()
        KE.clear_meshes()
        name = r['name']
        try:
            res = r['fn']()
            mb, hulls = res[0], res[1]
            ob = KE.build_object(name, mb)
            st = KE.mesh_stats(ob)
            if not hulls and r['category'] in SOLID_BUILDINGS:
                hulls = solid_building_hulls(st)
            cols = KE.build_collision(name, hulls) if hulls else []
            path = os.path.join(out, name + '.fbx')
            if not a.no_export:
                KE.export_fbx(ob, cols, path)
            if not a.no_preview:
                KE.render_preview(os.path.join(out, 'previews', name + '.png'), st['min'], st['max'], r['preview_dir'],
                                  a.res, ground=r['ground'], ground_z=min(0.0, st['min'][2]) if st['min'][2] > -0.5 else st['min'][2])
            size = [round(st['max'][i] - st['min'][i], 3) for i in range(3)]
            e = dict(name=name, file=name + '.fbx', category=r['category'], bounds_m=size,
                     bounds_min_m=[round(v, 3) for v in st['min']], bounds_max_m=[round(v, 3) for v in st['max']],
                     pivot=r['pivot'], notes=r['notes'], material_slots=st['materials'], triangles=st['tris'],
                     ucx_hulls=len(cols), preview='previews/%s.png' % name)
            entries.append(e)
            print('ASSET %-28s tris=%7d size=%s mats=%d dropped_openings=%d  %.1fs' % (
                name, st['tris'], size, len(st['materials']), len(KB.DROPPED), time.time() - t0), flush=True)
            for o in KB.DROPPED[:5]:
                print('   dropped:', {k: (round(v, 2) if isinstance(v, float) else v) for k, v in o.items() if k in ('kind', 'cx', 'sill', 'w', 'h', 'fw')})
            KB.DROPPED.clear()
        except Exception as ex:
            import traceback
            traceback.print_exc()
            print('FAILED', name, ex, flush=True)
    tag = 'only' if only else 'p%d' % k
    json.dump(entries, open(os.path.join(out, '_manifest_part_%s.json' % tag), 'w'), indent=1)


main()
