"""
verify_fbx.py - re-import every kit FBX into a fresh Blender scene, check bounds / UVs / materials / header.

  /snap/bin/blender -b --python verify_fbx.py -- --kit ~/gta-india/assets/kit
Writes <kit>/_verify_report.json and prints a table.
Expected: Blender re-import bounds == manifest bounds rotated 180 deg about Z (min_x' = -max_x, min_y' = -max_y),
FBX header UnitScaleFactor = 100, UpAxis = 2 (+Z), FrontAxis = 1 sign -1 (-Y), CoordAxis = 0 sign +1.
"""
import sys
import os
import json
import struct
import argparse
import bpy
from mathutils import Vector


def fbx_header_props(path, names=('UnitScaleFactor', 'UpAxis', 'UpAxisSign', 'FrontAxis', 'FrontAxisSign',
                                  'CoordAxis', 'CoordAxisSign', 'OriginalUnitScaleFactor')):
    data = open(path, 'rb').read()
    out = {}
    for n in names:
        key = b'S' + struct.pack('<I', len(n)) + n.encode()
        i = data.find(key)
        if i < 0:
            continue
        j = i + len(key)
        val = None
        for _ in range(8):
            t = data[j:j + 1]
            j += 1
            if t == b'S':
                ln = struct.unpack('<I', data[j:j + 4])[0]
                j += 4 + ln
            elif t == b'D':
                val = struct.unpack('<d', data[j:j + 8])[0]
                break
            elif t == b'I':
                val = struct.unpack('<i', data[j:j + 4])[0]
                break
            elif t == b'F':
                val = struct.unpack('<f', data[j:j + 4])[0]
                break
            elif t == b'L':
                val = struct.unpack('<q', data[j:j + 8])[0]
                break
            else:
                break
        out[n] = val
    return out


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--kit', default=os.path.expanduser('~/gta-india/assets/kit'))
    a = ap.parse_args(argv)
    kit = os.path.expanduser(a.kit)
    man = json.load(open(os.path.join(kit, 'kit_manifest.json')))
    report = []
    ok_all = True
    for e in man['assets']:
        path = os.path.join(kit, e['file'])
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=path)
        meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH' and not o.name.startswith('UCX_')]
        ucx = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name.startswith('UCX_')]
        pts = []
        uv_ok = True
        mats = []
        tris = 0
        for o in meshes:
            mw = o.matrix_world
            pts += [mw @ v.co for v in o.data.vertices]
            uv_ok = uv_ok and len(o.data.uv_layers) > 0
            mats += [m.name for m in o.data.materials if m]
            tris += sum(len(p.vertices) - 2 for p in o.data.polygons)
        mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        size = [round(mx[i] - mn[i], 3) for i in range(3)]
        exp_min = [-e['bounds_max_m'][0], -e['bounds_max_m'][1], e['bounds_min_m'][2]]
        err = max(abs(mn[i] - exp_min[i]) for i in range(3))
        hdr = fbx_header_props(path)
        ok = (err < 0.01 and uv_ok and len(meshes) == 1 and set(mats) == set(e['material_slots'])
              and abs((hdr.get('UnitScaleFactor') or 0) - 100.0) < 1e-6 and hdr.get('UpAxis') == 2
              and hdr.get('FrontAxis') == 1 and hdr.get('FrontAxisSign') == -1)
        ok_all = ok_all and ok
        r = dict(name=e['name'], ok=ok, reimport_size_m=size, reimport_min_m=[round(v, 3) for v in mn],
                 reimport_max_m=[round(v, 3) for v in mx], expected_min_m=[round(v, 3) for v in exp_min], err=round(err, 4),
                 mesh_objects=len(meshes), ucx=len(ucx), uv=uv_ok, tris=tris, header=hdr,
                 obj_scale=[round(s, 4) for s in meshes[0].scale] if meshes else None,
                 obj_rot=[round(s, 4) for s in meshes[0].rotation_euler] if meshes else None)
        report.append(r)
        print('VERIFY %-26s %s size=%s min=%s ucx=%d tris=%d unit=%s up=%s front=%s/%s' % (
            e['name'], 'OK ' if ok else 'BAD', size, r['reimport_min_m'], len(ucx), tris, hdr.get('UnitScaleFactor'),
            hdr.get('UpAxis'), hdr.get('FrontAxis'), hdr.get('FrontAxisSign')), flush=True)
    json.dump(dict(all_ok=ok_all, assets=report), open(os.path.join(kit, '_verify_report.json'), 'w'), indent=1)
    print('VERIFY_ALL', ok_all)


main()
