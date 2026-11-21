# Probe of the other families' exports for the Milestone 3 fixtures (read-only): the grip core and its parting line
# for the tang mould, the raw core's flash and sprue, the alloy offcuts for the charge, the vial for the press's pour
# place, the whole pistol for the holster, the servo for the tray.
#   SH/blender.sh fixtures/src/probe_m3.py  -> fixtures/layout/m3_probe.json
# Every family's own frame (metres, Z up); the pistol and grip frame P: muzzle -X, up +Z, the player's right +Y.
import bpy, bmesh, os, sys, json
import numpy as np
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
PROG = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(PROG, 'fixtures', 'layout', 'm3_probe.json')


def r(v, n=5):
    return [round(float(x), n) for x in v]


def mat(m):
    return [r(row, 6) for row in m]


def load(fam):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(os.path.join(PROG, fam, 'export', fam + '.blend'), link=False) as (src, dst):
        dst.objects = list(src.objects)
    for o in dst.objects:
        if o is not None:
            bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.update()
    P = {}
    for o in bpy.data.objects:
        if o.type == 'MESH' and 'sh' in o:
            P[json.loads(o['sh'])['id']] = o
    return P


def world_pts(o):
    dg = bpy.context.evaluated_depsgraph_get()
    oe = o.evaluated_get(dg); me = oe.to_mesh()
    co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    mw = np.array(oe.matrix_world)
    w = co @ mw[:3, :3].T + mw[:3, 3]
    oe.to_mesh_clear()
    return w


def info(o):
    w = world_pts(o)
    d = {'node': o.name, 'parent': o.parent.name if o.parent else None, 'matrix_world': mat(o.matrix_world),
         'world_min': r(w.min(0)), 'world_max': r(w.max(0)), 'verts': len(o.data.vertices)}
    loc = np.array([tuple(v.co) for v in o.data.vertices])
    d['local_min'] = r(loc.min(0)); d['local_max'] = r(loc.max(0))
    d['helpers'] = {e.name: mat(e.matrix_world) for e in bpy.data.objects if e.type == 'EMPTY' and e.name.startswith(o.name + '__')}
    return d


def section(o, plane_co, plane_no):
    """Outline loops where a plane cuts the object, in world coordinates."""
    bm = bmesh.new(); bm.from_mesh(o.data); bm.transform(o.matrix_world)
    res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-7, plane_co=plane_co, plane_no=plane_no)
    cut = [e for e in res['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]
    # chain the cut edges into loops
    adj = {}
    for e in cut:
        a, b = e.verts
        adj.setdefault(a, []).append(b); adj.setdefault(b, []).append(a)
    seen = set(); loops = []
    for v0 in list(adj):
        if v0 in seen:
            continue
        loop = [v0]; seen.add(v0); prev = None; cur = v0
        while True:
            nx = [w for w in adj[cur] if w is not prev and w not in seen]
            if not nx:
                break
            prev, cur = cur, nx[0]; seen.add(cur); loop.append(cur)
        loops.append([r(v.co) for v in loop])
    bm.free()
    loops.sort(key=len, reverse=True)
    return loops


res = {'note': 'model-bench probe for Milestone 3, read-only'}
# ---------------------------------------------------------------- grip core
P = load('grip')
core = P['grip.core']
res['grip_core'] = info(core)
w = world_pts(core)
res['grip_core']['half_bounds'] = {'y_neg': [r(w[w[:, 1] <= 0].min(0)), r(w[w[:, 1] <= 0].max(0))], 'y_pos': [r(w[w[:, 1] >= 0].min(0)), r(w[w[:, 1] >= 0].max(0))]}
res['grip_core']['section_y0'] = section(core, (0, 0, 0), (0, 1, 0))
res['grip_core']['tris'] = sum(len(p.vertices) - 2 for p in core.data.polygons)
res['grip_parts'] = {i: info(o) for i, o in P.items()}
# ---------------------------------------------------------------- materials: flash, sprue, offcuts, vial
P = load('materials')
keep = ['materials.core_flash', 'materials.core_flash_2', 'materials.core_flash_3', 'materials.core_sprue', 'materials.sheet_a', 'materials.sheet_a_offcut_1',
        'materials.sheet_a_offcut_2', 'materials.sheet_b', 'materials.sheet_b_offcut_1', 'materials.sheet_b_offcut_2', 'materials.vial', 'materials.vial_stopper',
        'materials.vial_fluid', 'materials.sheet_a_plate', 'materials.sheet_b_plate', 'materials.sheet_a_strap', 'materials.sheet_b_strap', 'materials.strap_bent',
        'materials.resistor', 'materials.sheet_a_margin', 'materials.sheet_b_margin']
res['materials'] = {i: info(P[i]) for i in keep if i in P}
gc = bpy.data.objects.get('grip_core')
res['materials_grip_core_standin'] = info(gc) if gc is not None and gc.type == 'MESH' else None
# offcut outlines: the top face (local, the face with the largest z)
for i in ('materials.sheet_a', 'materials.sheet_a_offcut_1', 'materials.sheet_a_offcut_2', 'materials.sheet_b_offcut_1', 'materials.sheet_b_offcut_2'):
    o = P[i]
    f = max(o.data.polygons, key=lambda p: (p.normal.z > 0.9) * p.area)
    res['materials'][i]['top_face_local'] = [r(o.data.vertices[k].co) for k in f.vertices]
# ---------------------------------------------------------------- pistol: everything as found, for the holster
P = load('pistol')
allw = np.vstack([world_pts(o) for i, o in P.items() if i not in ('pistol.card_a', 'pistol.card_b')])
res['pistol'] = {'all_min': r(allw.min(0)), 'all_max': r(allw.max(0)), 'frame': info(P['pistol.frame'])}
for x0 in np.arange(-0.30, 0.20, 0.01):
    m = (allw[:, 0] >= x0) & (allw[:, 0] < x0 + 0.01)
    if m.sum():
        q = allw[m]
        res['pistol'].setdefault('bins_x', []).append([round(float(x0 + 0.005), 3), r(q.min(0), 4), r(q.max(0), 4)])
# ---------------------------------------------------------------- servo
P = load('servo')
allw = np.vstack([world_pts(o) for i, o in P.items()])
res['servo'] = {'all_min': r(allw.min(0)), 'all_max': r(allw.max(0)), 'case_body': info(P['servo.case_body'])}
json.dump(res, open(OUT, 'w'), indent=1)
print('PROBE written', OUT)
