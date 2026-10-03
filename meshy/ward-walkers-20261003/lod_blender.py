"""Runtime LODs for a Ward NPC (headless Blender, Cycles CPU). Usage: blender.sh lod_blender.py -- <npc folder> <src glb> <lod0 tris> <lod1 tris>
The six 60k NPCs cost ~8.6 ms at cam_hill (native bisect, 3 Oct 01:05). This makes:
  LOD0: Decimate (collapse, triangulated) of the source welded by position to ~lod0 tris; UVs and vertex groups (skin)
        kept; smooth shading; head/neck protected through a vertex-group factor (args: pos 4) so the face keeps its
        density (unprotected, the face UVs smeared at conversation distance).
  LOD1: Decimate of LOD0 to ~lod1 tris (uses LOD0's map).
Writes <npc>/lod.npz: per LOD the glTF-ready vertex arrays (positions/normals/tangents in the source file's mesh space,
fitted from the untouched source vertices, UV with V flipped back, 4 joints/weights by bone name) and indices, plus
normal map: normal_smooth.png. glb_lod.py splices them into the rigged GLB (skin, armature and textures unchanged)."""
import bpy, sys, json, numpy as np
from pathlib import Path
a = sys.argv[sys.argv.index('--') + 1:]
D = Path(a[0]); SRC = a[1]; T0 = int(a[2]); T1 = int(a[3])
MODE = a[4] if len(a) > 4 else 'pos'      # pos: weld by position (UV seams become loop data) | posuv: rigged_smooth.glb, welded only where position+normal+UV match
PROTECT = float(a[5]) if len(a) > 5 else 0  # >0: Decimate vertex-group factor on the head/neck (keeps the face denser)
TAG = a[6] if len(a) > 6 else ''
bpy.ops.wm.read_factory_settings(use_empty=True)
s = bpy.context.scene; s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'; s.cycles.samples = 1
bpy.ops.import_scene.gltf(filepath=str(D / SRC), merge_vertices=False)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
src = max((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
for md in list(src.modifiers):
    if md.type == 'ARMATURE': src.modifiers.remove(md)
# keep the armature parent (its 0.01 scale makes world units metres for the bake distances); arrays use mesh-local coordinates
def tris(o): return sum(len(p.vertices) - 2 for p in o.data.polygons)

# glTF mesh-space <-> Blender mesh-local: affine fit on the untouched source (vertex i == glTF vertex i)
import struct
b = open(D / SRC, 'rb').read(); jl = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20 + jl]); base = 20 + jl + 8
prim = j['meshes'][0]['primitives'][0]
def acc(i, n):
    x = j['accessors'][i]; v = j['bufferViews'][x['bufferView']]; off = base + v.get('byteOffset', 0) + x.get('byteOffset', 0)
    return np.frombuffer(b, np.float32, x['count'] * n, off).reshape(-1, n)
G = acc(prim['attributes']['POSITION'], 3).astype(np.float64)
V = len(src.data.vertices); assert V == len(G), (V, len(G))
B0 = np.empty(V * 3); src.data.vertices.foreach_get('co', B0); B0 = B0.reshape(-1, 3)
X = np.hstack([B0, np.ones((V, 1))]); M, *_ = np.linalg.lstsq(X, G, rcond=None)   # G = [B 1] @ M
A3 = M[:3].T; t = M[3]; fit_err = float(np.abs(X @ M - G).max())
Ninv = np.linalg.inv(A3).T
joints = [j['nodes'][k]['name'] for k in j['skins'][0]['joints']]

def dup(o, name):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.duplicate(); d = bpy.context.view_layer.objects.active; d.name = name; d.data = d.data.copy(); return d

def decimate(o, target, protect=0):
    m = o.modifiers.new('dec', 'DECIMATE'); m.ratio = target / tris(o); m.use_collapse_triangulate = True
    if protect > 0: m.vertex_group = 'protect'; m.vertex_group_factor = protect; m.invert_vertex_group = True
    bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier=m.name)
    for p in o.data.polygons: p.use_smooth = True

# decimation source: the same file imported with merged vertices (the unmerged soup is split at every seam and flat
# normal, so a collapse would shrink each island on its own and tear the surface)
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(D / (SRC if MODE == 'pos' else 'rigged_smooth.glb')), merge_vertices=True)
newo = [o for o in bpy.data.objects if o not in before]
welded = max((o for o in newo if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
for md in list(welded.modifiers):
    if md.type == 'ARMATURE': welded.modifiers.remove(md)
assert (np.array(welded.matrix_world) - np.array(src.matrix_world)).__abs__().max() < 1e-6
for o in newo:
    if o != welded and o.type == 'MESH': bpy.data.objects.remove(o, do_unlink=True)
import bmesh
if MODE == 'pos':
    bm = bmesh.new(); bm.from_mesh(welded.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4); bm.to_mesh(welded.data); bm.free()
if PROTECT > 0:
    vg = welded.vertex_groups.new(name='protect'); hg = [welded.vertex_groups[n].index for n in ('Head', 'neck', 'head_end', 'headfront') if n in welded.vertex_groups]
    for v in welded.data.vertices:
        w = sum(g.weight for g in v.groups if g.group in hg)
        if w > 0.05: vg.add([v.index], min(1.0, w), 'REPLACE')
welded.data.update()
lo0 = dup(welded, 'lod0'); decimate(lo0, T0, PROTECT)
lo1 = dup(lo0, 'lod1'); decimate(lo1, T1)

# No bake here: a selected-to-active bake from the flat-normal source onto the decimated mesh came out with inverted
# (olive) texels per UV chart. Decimation keeps the UVs, so the LOD uses normal_smooth.png (rebake_normals.py: the
# source shading baked against smooth normals of the full mesh), which lines up with LOD0's smooth normals.

def export(o):
    me = o.data; me.calc_tangents(uvmap=me.uv_layers[0].name)
    n = len(me.loops)
    vi = np.empty(n, np.int64); me.loops.foreach_get('vertex_index', vi)
    nor = np.array([c.vector for c in me.corner_normals]) if hasattr(me, 'corner_normals') else np.array([l.normal for l in me.loops])
    tan = np.empty(n * 3); me.loops.foreach_get('tangent', tan); tan = tan.reshape(-1, 3)
    sg = np.empty(n); me.loops.foreach_get('bitangent_sign', sg)
    uv = np.empty(n * 2); me.uv_layers[0].data.foreach_get('uv', uv); uv = uv.reshape(-1, 2)
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    # skin: top 4 weights per vertex by bone name
    gname = {g.index: g.name for g in o.vertex_groups}
    J = np.zeros((len(me.vertices), 4), np.uint16); W = np.zeros((len(me.vertices), 4), np.float32)
    for v in me.vertices:
        ws = sorted(((g.weight, joints.index(gname[g.group])) for g in v.groups if gname[g.group] in joints and g.weight > 0), reverse=True)[:4]
        tot = sum(w for w, _ in ws) or 1
        for k, (w, ji) in enumerate(ws): J[v.index, k] = ji; W[v.index, k] = w / tot
    unweighted = int((W.sum(1) < .5).sum())
    # unique glTF vertices per (vertex, uv, normal, sign)
    key = np.hstack([vi[:, None].astype(np.float64), np.round(uv, 6), np.round(nor, 4), sg[:, None]])
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.ravel()
    P = co[vi[first]] @ A3.T + t
    N = nor[first] @ Ninv.T; N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-20
    Tg = tan[first] @ A3.T; Tg /= np.linalg.norm(Tg, axis=1, keepdims=True) + 1e-20
    T4 = np.hstack([Tg, -np.where(sg[first] >= 0, 1.0, -1.0)[:, None]])
    UV = uv[first].copy(); UV[:, 1] = 1 - UV[:, 1]
    loops_per_poly = np.array([len(p.vertices) for p in me.polygons]); assert (loops_per_poly == 3).all()
    I = inv.reshape(-1, 3)
    return dict(P=P.astype(np.float32), N=N.astype(np.float32), T=T4.astype(np.float32), UV=UV.astype(np.float32),
                J=J[vi[first]], W=W[vi[first]], I=I.astype(np.uint32)), unweighted

e0, u0 = export(lo0); e1, u1 = export(lo1)
np.savez(D / f'lod{TAG}.npz', **{f'l0_{k}': v for k, v in e0.items()}, **{f'l1_{k}': v for k, v in e1.items()})
rec = dict(mode=MODE, protect=PROTECT, welded_verts=len(welded.data.vertices), src=SRC, src_tris=tris(src), lod0_tris=tris(lo0), lod1_tris=tris(lo1), lod0_verts=len(e0['P']), lod1_verts=len(e1['P']),
           fit_err=fit_err, unweighted=[u0, u1])
(D / f'lod{TAG}.json').write_text(json.dumps(rec, indent=1)); print('LOD OK', json.dumps(rec))
