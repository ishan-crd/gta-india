"""
kit_export.py - turn kit_core.MB builders into Blender objects, world-scale UVs, FBX export, previews.

FBX / UE orientation
--------------------
Blender authoring space: metres, Z up, facades face -Y, ghat steps rise towards +Y.
UE's FBX importer converts the FBX right-handed scene to UE's left-handed space by mirroring Y
(FFbxDataConverter::ConvertPos -> (x, -y, z)).  A pure export would therefore turn a -Y facade into
a +Y facade in UE.  To make the imported asset match the spec (facade faces -Y, steps rise to +Y)
we bake a 180 deg rotation about Z into the exported mesh.  Net mapping (proper rotation, no mirroring):

        UE (x, y, z) [cm] = 100 * (-bx, by, bz)          (b = Blender authoring coords, metres)

Everything in the kit is centred on X (pivots at x = 0), so bounds are identical; only "left/right"
labels swap (Blender +X side appears at UE -X, exactly as a 180 deg yaw would do).

Export call (see export_fbx()):
    axis_forward='Y', axis_up='Z'   -> FBX GlobalSettings = Z-up, Front -Y, Coord +X, right handed,
                                        which is exactly UE's import axis system, so UE applies no
                                        extra axis conversion (global matrix is identity).
    apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS', global_scale=1.0
                                     -> FBX UnitScaleFactor = 100 (cm); 1 Blender m == 100 UE cm.
    use_triangles=True, mesh_smooth_type='FACE', use_tspace=False, bake_space_transform=False,
    object_types={'MESH'}, use_selection=True, add_leaf_bones=False, bake_anim=False, path_mode='STRIP'
"""
import math
import os
import bpy
import bmesh
from mathutils import Vector, Matrix

from kit_core import MB

# ---------------------------------------------------------------- preview colours (sRGB)
PALETTE = {
    'M_Sandstone': '#C9A06A', 'M_SandstoneRed': '#B36A4C', 'M_SandstoneSteps': '#C9A777', 'M_SandstoneOld': '#7C6B52',
    'M_Pavement': '#A87058', 'M_PlasterYellow': '#E6BC4E', 'M_PlasterOchre': '#D0913C', 'M_PlasterRed': '#B85A4C',
    'M_PlasterBlue': '#6F9DC4', 'M_PlasterPeeling': '#CBC1A9', 'M_PlasterMossy': '#8C8C6A', 'M_PlasterDamaged': '#C2AB8C',
    'M_PlasterWhite': '#EAE3D4', 'M_PlasterPainted': '#DA8D92', 'M_PlasterWorn': '#C9B28C', 'M_ClayPlaster': '#BA946C',
    'M_BrickPlaster': '#A5654E', 'M_BrickWhite': '#DCD6CA', 'M_Mud': '#6B5038', 'M_MudDry': '#9D8567',
    'M_Dirt': '#8F7559', 'M_DryGround': '#A68F6D', 'M_Trail': '#8C806F', 'M_Riverbed': '#8F7D63',
    'M_RiverPebbles': '#7F766A', 'M_RoadDamaged': '#5A5652', 'M_Asphalt': '#454341', 'M_CorrugatedRust': '#8B5335',
    'M_Shutter': '#77736B', 'M_WoodShutter': '#6B4A2E', 'M_WoodPlanks': '#7C5B3B', 'M_RoofTiles': '#A24F35',
    'M_Cloth': '#C8454A', 'M_MetalRust': '#6F4B37', 'M_Concrete': '#9B968D', 'M_Thatch': '#BC9F60',
    'M_Ballast': '#6F6A63', 'M_Steel': '#5D5955', 'M_WindowDark': '#141113', 'M_Saffron': '#F28014',
    'M_Gold': '#D8A838', 'M_Whitewash': '#EFEADF', 'M_Signboard': '#2F6FB0',
    'KitPreviewGround': '#9C9384', 'KitPreviewWater': '#4F5A4A',
}


def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_lin(h):
    h = h.lstrip('#')
    return tuple(srgb_to_lin(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4))


def get_material(name):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        try:
            m.use_nodes = True
        except Exception:
            pass
        col = hex_lin(PALETTE.get(name, '#FF00FF'))
        m.diffuse_color = (*col, 1.0)
        nt = m.node_tree
        if nt:
            bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if bsdf:
                bsdf.inputs['Base Color'].default_value = (*col, 1.0)
                bsdf.inputs['Roughness'].default_value = 0.35 if name in ('M_Gold', 'M_Steel') else 0.85
                if name == 'M_Gold':
                    bsdf.inputs['Metallic'].default_value = 0.9
    return m


# ---------------------------------------------------------------- mesh creation
def world_uv(p, n):
    ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
    if az >= ax and az >= ay:
        return (p.x / 2.0, (p.y if n.z >= 0 else -p.y) / 2.0)
    if ax >= ay:
        return ((p.y if n.x >= 0 else -p.y) / 2.0, p.z / 2.0)
    return ((-p.x if n.y >= 0 else p.x) / 2.0, p.z / 2.0)


def build_object(name, mb, weld=0.0004, smooth_angle=35.0, collection=None):
    """Create a Blender mesh object from an MB. Returns the object."""
    mats = []
    mat_index = {}
    for m in mb.m:
        if m not in mat_index:
            mat_index[m] = len(mats)
            mats.append(m)
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in mb.v], [], mb.f)
    me.polygons.foreach_set('material_index', [mat_index[m] for m in mb.m])
    # uv override id per face
    uvo_list = []
    ids = []
    for u in mb.uvo:
        if u is None:
            ids.append(0)
        else:
            uvo_list.append(u)
            ids.append(len(uvo_list))
    attr = me.attributes.new('kit_uvo', 'INT', 'FACE')
    attr.data.foreach_set('value', ids)
    me.update()

    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=weld)
    # remove degenerate faces
    bad = [f for f in bm.faces if f.calc_area() < 1e-9]
    if bad:
        bmesh.ops.delete(bm, geom=bad, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
    for f in bm.faces:
        f.smooth = True
    lim = math.radians(smooth_angle)
    for e in bm.edges:
        if len(e.link_faces) != 2:
            e.smooth = False
        else:
            try:
                e.smooth = e.calc_face_angle() < lim
            except ValueError:
                e.smooth = False
    bm.to_mesh(me)
    bm.free()

    # UVs: world scale box projection, 1 UV = 2 m (planar 0..1 override for signboards)
    uvl = me.uv_layers.new(name='UVMap')
    ids = [0] * len(me.polygons)
    if 'kit_uvo' in me.attributes:
        me.attributes['kit_uvo'].data.foreach_get('value', ids)
    verts = me.vertices
    uvdata = uvl.data
    for poly in me.polygons:
        n = poly.normal
        oid = ids[poly.index]
        for li in poly.loop_indices:
            p = verts[me.loops[li].vertex_index].co
            if oid:
                o, u, v, w, h = uvo_list[oid - 1]
                d = p - o
                uvdata[li].uv = (d.dot(u) / w, d.dot(v) / h)
            else:
                uvdata[li].uv = world_uv(p, n)
    if 'kit_uvo' in me.attributes:
        me.attributes.remove(me.attributes['kit_uvo'])
    for m in mats:
        me.materials.append(get_material(m))
    me.validate(clean_customdata=False)
    me.update()
    ob = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(ob)
    return ob


def build_collision(name, hulls, collection=None):
    """hulls: list of point lists (convex). Creates UCX_<name>_NN objects (convex hull via bmesh)."""
    obs = []
    for i, pts in enumerate(hulls):
        me = bpy.data.meshes.new('UCX_%s_%02d' % (name, i))
        bm = bmesh.new()
        vs = [bm.verts.new(p) for p in pts]
        bmesh.ops.convex_hull(bm, input=vs)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new('UCX_%s_%02d' % (name, i), me)
        (collection or bpy.context.scene.collection).objects.link(ob)
        ob.display_type = 'WIRE'
        ob.hide_render = True
        obs.append(ob)
    return obs


def mesh_stats(ob):
    me = ob.data
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    return dict(tris=tris, verts=len(me.vertices), min=(min(xs), min(ys), min(zs)), max=(max(xs), max(ys), max(zs)),
                materials=[m.name for m in me.materials])


ROT180 = Matrix.Rotation(math.pi, 4, 'Z')


def export_fbx(ob, colliders, path):
    """Export ob (+ UCX colliders) to FBX with the 180deg bake described in the module doc."""
    for o in bpy.context.scene.objects:
        o.select_set(False)
    objs = [ob] + list(colliders)
    for o in objs:
        o.data.transform(ROT180)
        o.select_set(True)
    bpy.context.view_layer.objects.active = ob
    try:
        bpy.ops.export_scene.fbx(
            filepath=path, use_selection=True, object_types={'MESH'},
            global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
            axis_forward='Y', axis_up='Z', bake_space_transform=False,
            use_mesh_modifiers=True, mesh_smooth_type='FACE', use_triangles=True, use_tspace=False,
            use_custom_props=False, add_leaf_bones=False, bake_anim=False, path_mode='STRIP',
            embed_textures=False, colors_type='NONE')
    finally:
        for o in objs:
            o.data.transform(ROT180)   # 180 twice = identity -> restore authoring orientation
            o.select_set(False)


# ---------------------------------------------------------------- preview rendering
def setup_scene(res=512):
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x = res
    sc.render.resolution_y = res
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = 'PNG'
    try:
        sc.view_settings.view_transform = 'AgX'
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    ee = sc.eevee
    for attr, val in (('taa_render_samples', 32), ('use_shadows', True), ('use_raytracing', False)):
        if hasattr(ee, attr):
            try:
                setattr(ee, attr, val)
            except Exception:
                pass
    # remove factory startup objects (cube, point light, camera)
    for o in list(bpy.data.objects):
        if o.name in ('Cube', 'Light', 'Camera'):
            bpy.data.objects.remove(o, do_unlink=True)
    # world: golden-hour gradient sky (warm horizon, soft blue zenith)
    w = bpy.data.worlds.get('KitWorld')
    if w is None:
        w = bpy.data.worlds.new('KitWorld')
        try:
            w.use_nodes = True
        except Exception:
            pass
        nt = w.node_tree
        bg = next(n for n in nt.nodes if n.type == 'BACKGROUND')
        tc = nt.nodes.new('ShaderNodeTexCoord')
        sep = nt.nodes.new('ShaderNodeSeparateXYZ')
        ramp = nt.nodes.new('ShaderNodeValToRGB')
        nt.links.new(tc.outputs['Generated'], sep.inputs[0])
        nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
        cr = ramp.color_ramp
        # Generated Z of the world = view direction z in [-1, 1]; horizon = 0
        cr.elements[0].position = 0.0
        cr.elements[0].color = (*hex_lin('#F4C38C'), 1)
        cr.elements[1].position = 0.5
        cr.elements[1].color = (*hex_lin('#8FAECB'), 1)
        e = cr.elements.new(0.12)
        e.color = (*hex_lin('#EBCDB0'), 1)
        nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
        bg.inputs['Strength'].default_value = 1.0
    sc.world = w
    # sun
    sun = bpy.data.objects.get('KitSun')
    if sun is None:
        ld = bpy.data.lights.new('KitSun', 'SUN')
        ld.energy = 4.5
        ld.color = (1.0, 0.84, 0.66)
        ld.angle = math.radians(1.5)
        sun = bpy.data.objects.new('KitSun', ld)
        sc.collection.objects.link(sun)
    # low sun from the river side (-Y), a bit from +X  (morning sun on the ghats)
    sun.rotation_euler = (math.radians(68), 0, math.radians(-28))
    cam = bpy.data.objects.get('KitCam')
    if cam is None:
        cd = bpy.data.cameras.new('KitCam')
        cam = bpy.data.objects.new('KitCam', cd)
        sc.collection.objects.link(cam)
    sc.camera = cam
    return sc


def ground_plane(z=0.0, size=400.0, mat='KitPreviewGround'):
    ob = bpy.data.objects.get('KitGround')
    if ob is None:
        mb = MB()
        s = size / 2
        mb.face([(-s, -s, z), (s, -s, z), (s, s, z), (-s, s, z)], mat, normal=(0, 0, 1))
        ob = build_object('KitGround', mb)
    return ob


def frame_camera(bmin, bmax, direction=(-0.55, -1.0, 0.5), lens=50.0, margin=1.12):
    cam = bpy.data.objects['KitCam']
    cam.data.lens = lens
    cam.data.clip_end = 5000
    c = (Vector(bmin) + Vector(bmax)) / 2
    ext = Vector(bmax) - Vector(bmin)
    r = ext.length / 2 * margin
    fov = 2 * math.atan(18.0 / lens)  # sensor 36mm
    dist = r / math.sin(fov / 2)
    d = Vector(direction).normalized()
    cam.location = c + d * dist
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    cam.data.clip_start = max(0.05, dist / 1000)


def render_preview(path, bmin, bmax, direction=(-0.55, -1.0, 0.5), res=512, ground=True, ground_z=None):
    sc = setup_scene(res)
    g = bpy.data.objects.get('KitGround')
    if ground:
        gz = bmin[2] if ground_z is None else ground_z
        g = ground_plane(0.0)
        g.location.z = gz - 0.005
        g.hide_render = False
    elif g:
        g.hide_render = True
    frame_camera(bmin, bmax, direction)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def clear_meshes(keep=('KitGround',)):
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and o.name not in keep:
            me = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            if me.users == 0:
                bpy.data.meshes.remove(me)
