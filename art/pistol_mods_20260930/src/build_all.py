# Stage A: build the six Scrap Pistol mods, check hand clearance, unwrap into one shared atlas, bake PBR maps from the
# procedural authoring materials, assign the two runtime materials, save the source .blend and export the GLB.
# Usage: run_blender.sh src/build_all.py  (env PM_TEX=2048, PM_BAKE_SAMPLES=32)
import sys, os, json, math, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
import pm_common as C
import pm_geo as G
import pm_mats as PM
import mods_barrel as MB, mods_cell as MC, mods_grip as MG

T0 = time.time()
ART = C.ART
TEX = int(os.environ.get('PM_TEX', '2048'))
BS = int(os.environ.get('PM_BAKE_SAMPLES', '32'))
EXPORT = ART + 'export/'
os.makedirs(EXPORT, exist_ok=True)
os.makedirs(ART + 'source', exist_ok=True)
LOG = {'date': '2026-09-30', 'tex': TEX}


def log(*a):
    print('[%6.1fs]' % (time.time() - T0), *a, flush=True)


C.reset()
pistol = C.import_pistol()
hands = C.import_hands()
M = PM.library()
ORDER = [('grip_stabilised_pistol', MG.build_stabilised), ('grip_gyro_braced', MG.build_gyro),
         ('barrel_bored_alloy', MB.build_bored_alloy), ('barrel_lattice_focused', MB.build_lattice_focused),
         ('cell_salvaged_capacitor', MC.build_capacitor), ('cell_overclocked', MC.build_overclocked)]
mods = {}
muzzles = {}
for name, fn in ORDER:
    o, extra = fn(M)
    o.name = name; o.data.name = name
    mods[name] = o
    if isinstance(extra, Vector):
        muzzles[name] = extra
    elif extra:
        LOG.setdefault('build_notes', {})[name] = extra
    log('built', name, G.tris(o))


# ------------------------------------------------------------------ clearance vs FP hands and pistol
def bvh_of(objs):
    bm = bmesh.new()
    for ob in objs:
        t = bmesh.new(); t.from_mesh(ob.data); t.transform(ob.matrix_world)
        me = bpy.data.meshes.new('_t'); t.to_mesh(me); t.free(); bm.from_mesh(me); bpy.data.meshes.remove(me)
    tr = BVHTree.FromBMesh(bm); bm.free(); return tr


HB = bvh_of(hands)
clear = {}
for name, o in mods.items():
    ins, mind, near1 = 0, 1.0, 0
    for v in o.data.vertices:
        p = o.matrix_world @ v.co
        nn = HB.find_nearest(p, 0.05)
        if nn[0] is None:
            continue
        inside = (p - nn[0]).dot(nn[1]) < 0
        if inside:
            ins += 1
        else:
            mind = min(mind, nn[3])
            if nn[3] < 0.001:
                near1 += 1
    clear[name] = {'verts': len(o.data.vertices), 'verts_inside_hands': ins, 'verts_within_1mm_of_hands': near1,
                   'min_gap_mm': round(mind * 1000, 2)}
    log('clearance', name, clear[name])
LOG['hand_clearance'] = clear

# ------------------------------------------------------------------ UVs: smart project each, pack all into one atlas
bpy.ops.object.select_all(action='DESELECT')
for o in mods.values():
    o.select_set(True)
bpy.context.view_layer.objects.active = mods['barrel_bored_alloy']
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(58), island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
bpy.ops.uv.select_all(action='SELECT')
bpy.ops.uv.average_islands_scale()
try:
    bpy.ops.uv.pack_islands(rotate=True, margin_method='FRACTION', margin=0.002, shape_method='CONCAVE')
except TypeError:
    bpy.ops.uv.pack_islands(rotate=True, margin=0.002)
bpy.ops.object.mode_set(mode='OBJECT')
texel = {}
for name, o in mods.items():
    me = o.data
    uv = me.uv_layers.active.data
    a3 = a2 = 0.0
    for p in me.polygons:
        a3 += p.area
        pts = [uv[li].uv for li in p.loop_indices]
        for i in range(1, len(pts) - 1):
            a2 += abs((pts[i] - pts[0]).cross(pts[i + 1] - pts[0])) / 2
    texel[name] = {'uv_fraction': round(a2, 4), 'texels_per_mm': round(math.sqrt(a2 * TEX * TEX / (a3 * 1e6)), 2)}
LOG['uv'] = texel
log('uv', texel)

# ------------------------------------------------------------------ bake
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.render.threads_mode = 'FIXED'; sc.render.threads = 16
sc.render.bake.margin = 0
sc.render.bake.use_clear = False
C.world_sky(strength=1.0)
sc.world.light_settings.distance = 0.012
for h in hands:
    h.hide_render = True


def new_img(name, noncolor, alpha0=True):
    im = bpy.data.images.new(name, TEX, TEX, alpha=True, float_buffer=False)
    im.colorspace_settings.name = 'Non-Color' if noncolor else 'sRGB'
    px = np.zeros(TEX * TEX * 4, np.float32)
    im.pixels.foreach_set(px)
    return im


IM = {'base': new_img('PM_base', False), 'metal': new_img('PM_metal', True), 'rough': new_img('PM_rough', True),
      'emit': new_img('PM_emit', False), 'normal': new_img('PM_normal', True), 'ao': new_img('PM_ao', True)}
mats_used = set()
for o in mods.values():
    for s in o.material_slots:
        if s.material:
            mats_used.add(s.material)


def set_target(img):
    for m in mats_used:
        nt = m.node_tree
        n = nt.nodes.get('BAKE_TGT') or nt.nodes.new('ShaderNodeTexImage')
        n.name = 'BAKE_TGT'; n.image = img
        nt.nodes.active = n


def route(channel):
    for m in mats_used:
        nt = m.node_tree
        out = nt.nodes['OUT']
        em = nt.nodes.get('BAKE_EM') or nt.nodes.new('ShaderNodeEmission')
        em.name = 'BAKE_EM'; em.inputs['Strength'].default_value = 1.0
        for l in list(em.inputs['Color'].links):
            nt.links.remove(l)
        if channel is None:
            nt.links.new(nt.nodes['BSDF'].outputs[0], out.inputs['Surface'])
        else:
            nt.links.new(nt.nodes['CH_' + channel].outputs[0], em.inputs['Color'])
            nt.links.new(em.outputs[0], out.inputs['Surface'])


def bake_all(kind, channel, img, samples):
    set_target(img)
    route(channel)
    sc.cycles.samples = samples
    for name, o in mods.items():
        for oo in mods.values():
            oo.hide_render = oo is not o
        bpy.ops.object.select_all(action='DESELECT')
        o.select_set(True); bpy.context.view_layer.objects.active = o
        if kind == 'NORMAL':
            bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', normal_r='POS_X', normal_g='POS_Y', normal_b='POS_Z',
                                margin=0, use_clear=False)
        elif kind == 'AO':
            bpy.ops.object.bake(type='AO', margin=0, use_clear=False)
        else:
            bpy.ops.object.bake(type='EMIT', margin=0, use_clear=False)
    for oo in mods.values():
        oo.hide_render = False
    route(None)
    log('baked', kind, channel)


bake_all('EMIT', 'base', IM['base'], BS)
bake_all('EMIT', 'metal', IM['metal'], BS)
bake_all('EMIT', 'rough', IM['rough'], BS)
bake_all('EMIT', 'emit', IM['emit'], max(8, BS // 2))
bake_all('NORMAL', None, IM['normal'], BS)
bake_all('AO', None, IM['ao'], max(48, BS))


# ------------------------------------------------------------------ gutters (dilate into unbaked pixels) and compose
def arr(img):
    a = np.empty(TEX * TEX * 4, np.float32); img.pixels.foreach_get(a)
    return a.reshape(TEX, TEX, 4)


def dilate(a, iters=16):
    a = a.copy()
    filled = a[..., 3] > 0.5
    for _ in range(iters):
        if filled.all():
            break
        acc = np.zeros_like(a[..., :3]); cnt = np.zeros(filled.shape, np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            sh = np.roll(np.roll(a[..., :3], dy, 0), dx, 1)
            sf = np.roll(np.roll(filled, dy, 0), dx, 1)
            acc += sh * sf[..., None]; cnt += sf
        new = (~filled) & (cnt > 0)
        a[new, :3] = acc[new] / cnt[new][:, None]
        filled = filled | new
    a[~filled, :3] = a[filled, :3].mean(0) if filled.any() else 0
    a[..., 3] = 1.0
    return a, filled


A = {k: arr(v) for k, v in IM.items()}
cover = A['base'][..., 3] > 0.5
LOG['atlas_coverage'] = round(float(cover.mean()), 3)
D = {}
for k in A:
    D[k], _ = dilate(A[k], 24)
log('dilated')


def save(name, rgba, noncolor):
    im = bpy.data.images.new(name, TEX, TEX, alpha=True, float_buffer=False)
    im.colorspace_settings.name = 'Non-Color' if noncolor else 'sRGB'
    im.pixels.foreach_set(rgba.astype(np.float32).ravel())
    im.filepath_raw = EXPORT + name + '.png'
    im.file_format = 'PNG'
    im.save()
    return im


def rgb(a, alpha=None):
    out = np.ones((TEX, TEX, 4), np.float32)
    out[..., :3] = np.clip(a, 0, 1)
    if alpha is not None:
        out[..., 3] = np.clip(alpha, 0, 1)
    return out


metal = D['metal'][..., 0]; rough = D['rough'][..., 0]; ao = D['ao'][..., 0]
img_base = save('PistolMods_BaseColor', rgb(D['base'][..., :3]), False)
img_norm = save('PistolMods_Normal', rgb(D['normal'][..., :3]), True)
mask = np.stack([metal, ao, np.zeros_like(ao)], -1)
img_mask = save('PistolMods_MaskMap', rgb(mask, 1.0 - rough), True)
img_orm = save('PistolMods_ORM_gltf', rgb(np.stack([ao, rough, metal], -1)), True)
emit_rgb = D['emit'][..., :3]
emit_rgb = emit_rgb / max(1e-6, float(emit_rgb.max()))
img_emit = save('PistolMods_Emission', rgb(emit_rgb), False)
LOG['texture_stats'] = {'metal_mean': round(float(metal[cover].mean()), 3), 'rough_mean': round(float(rough[cover].mean()), 3),
                        'ao_mean': round(float(ao[cover].mean()), 3), 'emit_max_raw': round(float(D['emit'][..., :3].max()), 3)}
log('saved textures', LOG['texture_stats'])


# ------------------------------------------------------------------ runtime materials (2 slots)
def runtime_mat(name, emissive):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    tb = nt.nodes.new('ShaderNodeTexImage'); tb.image = img_base
    nt.links.new(tb.outputs['Color'], b.inputs['Base Color'])
    to = nt.nodes.new('ShaderNodeTexImage'); to.image = img_orm
    sp = nt.nodes.new('ShaderNodeSeparateColor')
    nt.links.new(to.outputs['Color'], sp.inputs[0])
    nt.links.new(sp.outputs['Green'], b.inputs['Roughness'])
    nt.links.new(sp.outputs['Blue'], b.inputs['Metallic'])
    tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = img_norm
    nm = nt.nodes.new('ShaderNodeNormalMap')
    nt.links.new(tn.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    # glTF occlusion (R of the ORM texture) through the exporter's settings group
    grp = bpy.data.node_groups.get('glTF Material Output')
    if not grp:
        grp = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
        grp.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
    gn = nt.nodes.new('ShaderNodeGroup'); gn.node_tree = grp
    nt.links.new(sp.outputs['Red'], gn.inputs['Occlusion'])
    if emissive:
        te = nt.nodes.new('ShaderNodeTexImage'); te.image = img_emit
        nt.links.new(te.outputs['Color'], b.inputs['Emission Color'])
        b.inputs['Emission Strength'].default_value = 4.0
    return m


MAT0 = runtime_mat('MI_PistolMods', False)
MAT1 = runtime_mat('MI_PistolMods_Emissive', True)
slot_tris = {}
for name, o in mods.items():
    me = o.data
    emis = [bool(s.material.get('emissive', 0)) if s.material else False for s in o.material_slots]
    idx = [1 if emis[p.material_index] else 0 for p in me.polygons]
    me.materials.clear()
    me.materials.append(MAT0); me.materials.append(MAT1)
    for p, i in zip(me.polygons, idx):
        p.material_index = i
    slot_tris[name] = {'MI_PistolMods': sum(len(p.vertices) - 2 for p in me.polygons if p.material_index == 0),
                       'MI_PistolMods_Emissive': sum(len(p.vertices) - 2 for p in me.polygons if p.material_index == 1)}
LOG['tris'] = {n: G.tris(o) for n, o in mods.items()}
LOG['material_slot_tris'] = slot_tris

# ------------------------------------------------------------------ source .blend (metric frame, on the pistol)
for im in (img_base, img_norm, img_mask, img_orm, img_emit):
    im.filepath = EXPORT + im.name + '.png'
bpy.ops.wm.save_as_mainfile(filepath=ART + 'source/pistol_mods_v1.blend', compress=True)
log('saved blend')

# ------------------------------------------------------------------ export: pistol glTF units, identity transforms
for h in hands:
    bpy.data.objects.remove(h, do_unlink=True)
bpy.data.objects.remove(pistol, do_unlink=True)
Sinv = Matrix.Scale(1.0 / C.S, 4)
for o in mods.values():
    o.data.transform(Sinv)
    o.matrix_world = Matrix.Identity(4)
bpy.ops.object.select_all(action='DESELECT')
for o in mods.values():
    o.select_set(True)
bpy.context.view_layer.objects.active = mods['barrel_bored_alloy']
out = EXPORT + 'PistolMods.glb'
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
                          export_texcoords=True, export_normals=True, export_tangents=True, export_materials='EXPORT',
                          export_image_format='AUTO', export_extras=False)
log('exported', out, os.path.getsize(out))


# ------------------------------------------------------------------ manifest: muzzles in every frame the integrator needs
def frames(pm):
    g = C.metric_to_gltf(pm)
    unity_local = Vector((-g.x, g.y, g.z))                       # glTFast negates X
    holder = Vector((-C.S * g.z + C.HOLDER_T.x, C.S * g.y + C.HOLDER_T.y, -C.S * g.x + C.HOLDER_T.z))
    r = lambda v: [round(x, 5) for x in v]
    return {'gltf_pistol_units': r(g), 'unity_pistol_mesh_local': r(unity_local), 'unity_holder_metres': r(holder),
            'metric_blender': r(pm)}


LOG['muzzle_points'] = {n: frames(p) for n, p in muzzles.items()}
LOG['muzzle_points']['stock_pistol_reference'] = frames(C.unity_holder_to_metric((0.00079, 0.02989, 0.21389)))
json.dump(LOG, open(EXPORT + 'mods_manifest.json', 'w'), indent=1)
log('DONE', json.dumps(LOG['tris']))
