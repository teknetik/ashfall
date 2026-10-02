"""Feral lancer drone: orient, scale, replace the four fused rotors, fit the eye lens cap and the muzzle (Blender 5.2).
Usage: blender.sh process_lancer.py -- <model.glb> <out folder> [span_m=1.8] [lens_radius_m=0]
Writes <out>/FeralLancer.glb: root 'FeralLancer' > 'Body' (hull + ducts + authored static motor pods/stators),
'Rotor A'..'Rotor D' (authored three-blade rotors + spinner, pivot on the hub, spin axis local Y in glTF/Unity),
'Lens cap' (emissive dome over the eye), 'Muzzle' (empty at the lance tip, +Z out of the barrel). glTF +Z forward,
+Y up; origin at the centre of lift (rotor hubs' centroid) at the hull's mid-height. No embedded images (the Unity
materials use the Meshy maps exported separately); the authored parts carry UVs transferred from the nearest removed
Meshy rotor vertices, so they share the body's material and atlas.
Rotors: A front-left, B front-right, C rear-left, D rear-right (robot's left = +X in glTF). The Meshy rotor blades were
fused into the ducts and warped (curled, holed, shards: renders/lancer_a1/*, first split attempt), so everything inside
each duct's inner wall is replaced. Writes <out>/lancer.json and review renders in <out>/renders/."""
import bpy, bmesh, sys, json, math
from pathlib import Path
from mathutils import Vector, Matrix, kdtree
import numpy as np
args = sys.argv[sys.argv.index('--') + 1:]
SRC, OUT = Path(args[0]), Path(args[1]); SPAN = float(args[2]) if len(args) > 2 else 1.8
LENS_R = float(args[3]) if len(args) > 3 else 0.0
OUT.mkdir(parents=True, exist_ok=True); REN = OUT / 'renders'; REN.mkdir(exist_ok=True)
rec = {'source': str(SRC), 'target_span_m': SPAN}

bpy.ops.wm.read_factory_settings(use_empty=True)
s = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=str(SRC))
meshes = [o for o in s.objects if o.type == 'MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in meshes: o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1: bpy.ops.object.join()
obj = bpy.context.view_layer.objects.active
for o in list(s.objects):
    if o is not obj and o.type == 'EMPTY': bpy.data.objects.remove(o)
obj.parent = None
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
# the Meshy drone faces glTF -X (lance tip: the narrow extreme at -X, below the hull) = Blender -X; turn it to face -Y
obj.rotation_mode = 'XYZ'; obj.rotation_euler = (0, 0, math.pi / 2); bpy.ops.object.transform_apply(rotation=True)
me = obj.data
def verts():
    co = np.empty(len(me.vertices) * 3, np.float64); me.vertices.foreach_get('co', co); return co.reshape(-1, 3)
co = verts(); lo, hi = co.min(0), co.max(0)
scale = SPAN / (hi[0] - lo[0])
obj.scale = (scale,) * 3; bpy.ops.object.transform_apply(scale=True)
co = verts(); lo, hi = co.min(0), co.max(0)
rec['scale_applied'] = round(scale, 5)
mat = me.materials[0]

# ------------------------------------------------------------------ ducts: centre, outer/inner wall radius, height band
def circle_fit(p):
    A = np.c_[2 * p[:, 0], 2 * p[:, 1], np.ones(len(p))]; b = (p[:, :2] ** 2).sum(1)
    c, *_ = np.linalg.lstsq(A, b, rcond=None); return np.array(c[:2]), math.sqrt(c[2] + c[0] ** 2 + c[1] ** 2)
ducts = []
for name, sx, sy in (('Rotor A', 1, -1), ('Rotor B', -1, -1), ('Rotor C', 1, 1), ('Rotor D', -1, 1)):
    q = co[(co[:, 0] * sx > .3)]
    # front/rear duct on this side: two-means in Y
    m0, m1 = float(q[:, 1].min()), float(q[:, 1].max())
    for _ in range(20):
        front_ = np.abs(q[:, 1] - m0) < np.abs(q[:, 1] - m1); m0, m1 = float(q[front_, 1].mean()), float(q[~front_, 1].mean())
    q = q[front_] if sy < 0 else q[~front_]
    c = (q[:, :2].min(0) + q[:, :2].max(0)) / 2
    for _ in range(8):
        d = np.linalg.norm(q[:, :2] - c, axis=1)
        R = np.percentile(d[d < .7], 98)
        wall = q[(d > .85 * R) & (d < 1.04 * R)]
        c, R = circle_fit(wall[:, :2])
    d = np.linalg.norm(q[:, :2] - c, axis=1)
    ring = q[(d > .88 * R) & (d < 1.04 * R)]
    zlo, zhi = float(np.percentile(ring[:, 2], 2)), float(np.percentile(ring[:, 2], 98))
    # inner wall: the smallest radius (> 0.55 R) at which >= 85 % of 48 angular sectors hold a vertex in the band
    band = co[(np.linalg.norm(co[:, :2] - c, axis=1) < R * 1.02) & (co[:, 2] > zlo) & (co[:, 2] < zhi)]
    rr = np.linalg.norm(band[:, :2] - c, axis=1); th = np.arctan2(band[:, 1] - c[1], band[:, 0] - c[0])
    sec = ((th + math.pi) / (2 * math.pi) * 48).astype(int) % 48
    r_cov = .8 * R
    for r0 in np.arange(.55 * R, R, .004):
        m = (rr >= r0) & (rr < r0 + .012)
        if len(np.unique(sec[m])) >= 41: r_cov = float(r0); break
    r_in = float(R) - .02    # 2 cm wall (the coverage estimate r_cov is thrown off by blade shards stuck to the wall)
    ducts.append(dict(name=name, centre=c, R=float(R), r_in=r_in, r_cov=r_cov, zlo=zlo, zhi=zhi))
rec['ducts'] = [dict(name=d['name'], centre=[round(float(x), 4) for x in d['centre']], outer_radius=round(d['R'], 4),
                     inner_radius=round(d['r_in'], 4), coverage_radius=round(d['r_cov'], 4), z_band=[round(d['zlo'], 4), round(d['zhi'], 4)]) for d in ducts]

# ------------------------------------------------------------------ remove the fused Meshy rotors
bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table(); uvl = bm.loops.layers.uv.active
removed = {d['name']: [] for d in ducts}; kill = []
for f in bm.faces:
    c = f.calc_center_median(); n = f.normal
    for d in ducts:
        dx, dy = c.x - d['centre'][0], c.y - d['centre'][1]; r = math.hypot(dx, dy)
        radial = abs(n.x * dx + n.y * dy) / max(r, 1e-6)
        inside = r < .97 * d['r_in'] or (r < d['r_in'] + .012 and radial < .55)   # blade shards stuck to the wall
        if inside and d['zlo'] - .07 < c.z < d['zhi'] + .12:
            kill.append(f)
            for l in f.loops: removed[d['name']].append((*l.vert.co[:], *l[uvl].uv[:]))
            break
rec['meshy_rotor_faces_removed'] = len(kill)
bmesh.ops.delete(bm, geom=kill, context='FACES')
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
# leftover islands (blade shards on their own UV islands) whose centre lies inside a duct's inner wall
bm.verts.ensure_lookup_table(); bm.verts.index_update()
par = list(range(len(bm.verts)))
def fnd(i):
    while par[i] != i: par[i] = par[par[i]]; i = par[i]
    return i
for e in bm.edges:
    a_, b_ = fnd(e.verts[0].index), fnd(e.verts[1].index)
    if a_ != b_: par[a_] = b_
comp = {}
for v in bm.verts: comp.setdefault(fnd(v.index), []).append(v)
drop = []
for vs_ in comp.values():
    if len(vs_) > 400: continue
    for d in ducts:   # every vertex strictly inside the inner wall (wall islands are arcs that reach the wall)
        if all(math.hypot(v.co.x - d['centre'][0], v.co.y - d['centre'][1]) < d['r_in'] - .004 and d['zlo'] - .07 < v.co.z < d['zhi'] + .12 for v in vs_):
            drop.extend(vs_); break
rec['shard_islands_removed_vertices'] = len(drop)
bmesh.ops.delete(bm, geom=drop, context='VERTS')
bm.to_mesh(me); bm.free()

# ------------------------------------------------------------------ eye (before adding parts) and muzzle
co = verts()
img = next(n.image for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE' and any(l.to_socket.name == 'Base Color' for l in n.outputs['Color'].links))
W, H = img.size; px = np.empty(W * H * 4, np.float32); img.pixels.foreach_get(px); px = px.reshape(H, W, 4)
bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table(); uvl = bm.loops.layers.uv.active
C = np.array([f.calc_center_median()[:] for f in bm.faces]); N = np.array([f.normal[:] for f in bm.faces])
uvc = np.array([np.mean([l[uvl].uv[:] for l in f.loops], axis=0) for f in bm.faces])
col = px[np.clip((uvc[:, 1] * H).astype(int), 0, H - 1), np.clip((uvc[:, 0] * W).astype(int), 0, W - 1), :3]
mx_ = col.max(1); sat = (mx_ - col.min(1)) / np.maximum(mx_, 1e-4)
nose = (C[:, 1] < lo[1] + .5) & (np.abs(C[:, 0]) < .2) & (C[:, 2] > np.percentile(co[:, 2], 35))
hot = nose & (mx_ > .6) & (sat > .45) & (col[:, 0] >= col[:, 1]) & (col[:, 1] >= col[:, 2])
eye_faces = np.flatnonzero(hot)
rec['eye_candidate_faces'] = int(len(eye_faces))
ec = C[eye_faces]; wgt = mx_[eye_faces]
centre = (ec * wgt[:, None]).sum(0) / wgt.sum()
rad = float(np.percentile(np.linalg.norm(ec - centre, axis=1), 90))
nrm = N[eye_faces].mean(0); nrm /= np.linalg.norm(nrm)
# the eye looks forward: keep the lens cap facing mostly forward even if the glass faces were noisy
nrm = Vector(nrm).lerp(Vector((0, -1, 0)), .5).normalized()
rec['eye'] = dict(centre=[round(float(x), 4) for x in centre], glass_radius=round(rad, 4), normal=[round(x, 3) for x in nrm])
bm.free()
front = co[co[:, 1] < co[:, 1].min() + .012]
rec['muzzle'] = dict(tip_y=round(float(co[:, 1].min()), 4), bore_centre_xz=[round(float(front[:, 0].mean()), 4), round(float(front[:, 2].mean()), 4)])

# ------------------------------------------------------------------ authored parts
def uv_from(points, kd, uvs):
    return [uvs[kd.find(p)[1]] for p in points]

def add_part(bmp, verts_, faces_, kd, uvs, uvlayer):
    vs = [bmp.verts.new(v) for v in verts_]; made = []
    for fc in faces_:
        try: f = bmp.faces.new([vs[i] for i in fc])
        except ValueError: continue
        made.append(f)
    patch_uvs(bmp, made, uvlayer)
    bmesh.ops.recalc_face_normals(bmp, faces=made)
    return made

def cylinder(cx, cy, z0, z1, r, n=20, cap_top=True, cap_bot=True):
    V, F = [], []
    for z in (z0, z1):
        for k in range(n): a = 2 * math.pi * k / n; V.append((cx + r * math.cos(a), cy + r * math.sin(a), z))
    for k in range(n): F.append([k, (k + 1) % n, n + (k + 1) % n, n + k])
    if cap_bot: F.append(list(range(n))[::-1])
    if cap_top: F.append(list(range(n, 2 * n)))
    return V, F

def dome(cx, cy, z0, r, h, n=20, rings=4):
    V, F = [(cx, cy, z0 + h)], []
    for ri in range(1, rings + 1):
        f = ri / rings; a_ = f * math.pi / 2
        for k in range(n): a = 2 * math.pi * k / n; V.append((cx + r * math.sin(a_) * math.cos(a), cy + r * math.sin(a_) * math.sin(a), z0 + h * math.cos(a_)))
    for k in range(n): F.append([0, 1 + k, 1 + (k + 1) % n])
    for ri in range(1, rings):
        for k in range(n):
            a0 = 1 + (ri - 1) * n + k; a1 = 1 + (ri - 1) * n + (k + 1) % n; F.append([a0, a0 + n, a1 + n, a1])
    F.append([1 + (rings - 1) * n + k for k in range(n)][::-1])
    return V, F

def box(p0, p1, w, h):
    """Bar from p0 to p1 (horizontal), width w, height h."""
    p0, p1 = Vector(p0), Vector(p1); d = (p1 - p0).normalized(); side = d.cross(Vector((0, 0, 1))).normalized() * w / 2; up = Vector((0, 0, h / 2))
    V = [tuple(p + sv + uv) for p in (p0, p1) for sv, uv in ((side, up), (-side, up), (-side, -up), (side, -up))]
    F = [[0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7], [0, 3, 2, 1], [4, 5, 6, 7]]
    return V, F

def blade(r0, r1, theta, z, handed, n=7):
    """Twisted rotor blade along radius r0..r1 at angle theta; chord 0.085->0.05 m, pitch 26->11 deg, 7 mm thick."""
    V, F = [], []
    e = Vector((math.cos(theta), math.sin(theta), 0)); t = Vector((-math.sin(theta), math.cos(theta), 0)) * handed; zv = Vector((0, 0, 1))
    for i in range(n):
        f = i / (n - 1); r = r0 + (r1 - r0) * f
        chord = .085 - .035 * f; beta = math.radians(26 - 15 * f); th = .007 * (1 - .4 * f)
        cdir = t * math.cos(beta) + zv * math.sin(beta); ndir = -t * math.sin(beta) + zv * math.cos(beta)
        c = e * r + Vector((0, 0, z))
        sweep = t * (.012 * f * f)     # slight back-sweep of the tips
        for p in (c + cdir * chord * .5 + ndir * th * .3, c - cdir * chord * .5 + ndir * th * .5 + sweep,
                  c - cdir * chord * .5 - ndir * th * .5 + sweep, c + cdir * chord * .5 - ndir * th * .3):
            V.append(tuple(p))
    for i in range(n - 1):
        for k in range(4): F.append([4 * i + k, 4 * i + (k + 1) % 4, 4 * (i + 1) + (k + 1) % 4, 4 * (i + 1) + k])
    F.append([3, 2, 1, 0]); F.append([4 * (n - 1) + k for k in range(4)])
    return V, F

allR = np.concatenate([np.array(removed[d['name']]) for d in ducts])
cand = allR[::7]
cc = px[np.clip((cand[:, 4] * H).astype(int), 0, H - 1), np.clip((cand[:, 3] * W).astype(int), 0, W - 1), :3]
score = np.abs(cc - np.array([.2, .18, .16])).sum(1) + (cc.max(1) - cc.min(1)) * 2
STEEL_UV = cand[int(np.argmin(score)), 3:5]
rec['authored_parts_uv_patch'] = dict(centre=[round(float(x), 4) for x in STEEL_UV], colour=cc[int(np.argmin(score))].round(3).tolist(), size=.006)
class _Patch:
    def find(self, p): return (None, 0, 0)
def patch_uvs(bmp, faces, uvlayer):
    for f in faces:
        for l in f.loops:
            v = l.vert.co; l[uvlayer].uv = (STEEL_UV[0] + ((v.x * 7.1 + v.z * 3.3) % .006) - .003, STEEL_UV[1] + ((v.y * 7.1 + v.z * 2.9) % .006) - .003)
body_bm = bmesh.new(); body_bm.from_mesh(me); body_uv = body_bm.loops.layers.uv.active
rotor_objs, rotor_info = [], {}
# the hull top has a torn open hole (Meshy defect, renders/proc_hull_top.png): find it as a pit in a downward ray-cast
# height field over the hull top, then cover it with a bolted steel hatch plate
from mathutils.bvhtree import BVHTree
body_bm.faces.ensure_lookup_table()
bvh = BVHTree.FromBMesh(body_bm)
hull_y = [v.co.y for v in body_bm.verts if abs(v.co.x) < .2]
gy = np.arange(min(hull_y) + .3, max(hull_y) - .05, .01); gx = np.arange(-.2, .2001, .01)
Hf = np.full((len(gy), len(gx)), np.nan)
for i, y in enumerate(gy):
    for j, x in enumerate(gx):
        hit = bvh.ray_cast(Vector((x, y, 2.0)), Vector((0, 0, -1)))
        if hit[0] is not None: Hf[i, j] = hit[0].z
from numpy.lib.stride_tricks import sliding_window_view
pad = np.pad(np.nan_to_num(Hf, nan=-1), 6, mode='edge')
local = np.median(sliding_window_view(pad, (13, 13)), axis=(2, 3))
pit = (Hf < local - .05) & ~np.isnan(Hf) & (local > np.nanpercentile(Hf, 60))
hatch = None
if pit.sum() >= 4:
    ii, jj = np.nonzero(pit)
    # biggest connected pit
    lab = -np.ones(pit.shape, int); comps = []
    for a0, b0 in zip(ii, jj):
        if lab[a0, b0] >= 0: continue
        st = [(a0, b0)]; lab[a0, b0] = len(comps); cur = []
        while st:
            a1, b1 = st.pop(); cur.append((a1, b1))
            for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
                a2, b2 = a1 + da, b1 + db
                if 0 <= a2 < pit.shape[0] and 0 <= b2 < pit.shape[1] and pit[a2, b2] and lab[a2, b2] < 0: lab[a2, b2] = len(comps); st.append((a2, b2))
        comps.append(cur)
    big = max(comps, key=len)
    py_ = np.array([gy[a1] for a1, b1 in big]); px_ = np.array([gx[b1] for a1, b1 in big])
    hc = np.array([px_.mean(), py_.mean()]); hr = min(.16, float(np.hypot(px_ - hc[0], py_ - hc[1]).max()) + .03)
    rim = [local[a1, b1] for a1, b1 in big]
    top_z = float(np.max(rim))
    near_f = [f for f in body_bm.faces if abs(f.calc_center_median().x - hc[0]) < hr + .04 and abs(f.calc_center_median().y - hc[1]) < hr + .04 and f.calc_center_median().z > top_z - .04 and f.normal.z > .3]
    hn = sum((f.normal for f in near_f), Vector()).normalized() if near_f else Vector((0, 0, 1))
    base = Vector((float(hc[0]), float(hc[1]), top_z - .006))
    V, F = cylinder(0, 0, 0, .014, hr, n=24)
    q = Vector((0, 0, 1)).rotation_difference(hn)
    add_part(body_bm, [tuple(base + q @ Vector(v)) for v in V], F, None, None, body_uv)
    for k in range(6):   # bolt heads round the rim
        a_ = 2 * math.pi * (k + .5) / 6; bc = Vector((math.cos(a_) * (hr - .018), math.sin(a_) * (hr - .018), .014))
        Vb, Fb = cylinder(bc.x, bc.y, bc.z, bc.z + .008, .009, n=8)
        add_part(body_bm, [tuple(base + q @ Vector(v)) for v in Vb], Fb, None, None, body_uv)
    hatch = dict(centre=[round(float(x), 4) for x in base], radius=round(hr, 4), normal=[round(x, 3) for x in hn], pit_cells=len(big))
rec['hull_top_hatch'] = hatch
for d in ducts:
    R_ = np.array(removed[d['name']]); kd = kdtree.KDTree(len(R_))
    for i, p in enumerate(R_[:, :3]): kd.insert(p, i)
    kd.balance(); uvs = [tuple(x) for x in R_[:, 3:5]]
    cx, cy = float(d['centre'][0]), float(d['centre'][1]); zb = d['zlo'] + .62 * (d['zhi'] - d['zlo'])   # blade plane
    rin = d['r_in']
    # static: motor pod under the blades, three stator struts to the duct wall (at 60 deg to the blades' rest angles)
    for V, F in (cylinder(cx, cy, zb - .1, zb - .018, .05), dome(cx, cy, zb - .1, .05, -.035)):
        add_part(body_bm, V, F, kd, uvs, body_uv)
    for k in range(3):
        a = math.radians(30 + 120 * k)
        V, F = box((cx + .045 * math.cos(a), cy + .045 * math.sin(a), zb - .07), (cx + (rin + .012) * math.cos(a), cy + (rin + .012) * math.sin(a), zb - .07), .016, .011)
        add_part(body_bm, V, F, kd, uvs, body_uv)
    # rotor (pivot at the hub on the blade plane): spinner + shaft collar + three blades
    rbm = bmesh.new(); ruv = rbm.loops.layers.uv.new('UVMap')
    handed = 1 if d['name'] in ('Rotor A', 'Rotor D') else -1          # diagonal pairs share a spin direction
    for V, F in (dome(0, 0, .012, .045, .045), cylinder(0, 0, -.02, .012, .045), cylinder(0, 0, -.018 - .0, -.016, .03, cap_top=False)):
        add_part(rbm, [(x + cx, y + cy, z + zb) for x, y, z in V], F, kd, uvs, ruv)
    for k in range(3):
        V, F = blade(.035, .93 * rin, math.radians(90 + 120 * k), 0, handed)
        add_part(rbm, [(x + cx, y + cy, z + zb) for x, y, z in V], F, kd, uvs, ruv)
    for v in rbm.verts: v.co -= Vector((cx, cy, zb))
    bmesh.ops.recalc_face_normals(rbm, faces=rbm.faces)
    rme = bpy.data.meshes.new('FeralLancer_' + d['name'].replace(' ', '')); rbm.to_mesh(rme); rbm.free()
    rme.materials.append(mat); rme.polygons.foreach_set('use_smooth', [False] * len(rme.polygons))
    ro = bpy.data.objects.new(d['name'], rme); s.collection.objects.link(ro); ro.location = (cx, cy, zb)
    rotor_objs.append(ro)
    rotor_info[d['name']] = dict(pivot=[round(cx, 4), round(cy, 4), round(zb, 4)], blade_radius=round(.93 * rin, 4),
                                 spin_handedness=handed, triangles=sum(len(p.vertices) - 2 for p in rme.polygons))
body_bm.to_mesh(me); body_bm.free()
rec['rotors'] = rotor_info

# ------------------------------------------------------------------ origin: centre of lift, hull mid-height
hub = np.mean([r['pivot'] for r in rotor_info.values()], axis=0)
co = verts(); hull = co[(np.abs(co[:, 0]) < .3)]
origin = Vector((float(hub[0]), float(hub[1]), float((hull[:, 2].min() + hull[:, 2].max()) / 2)))
me.transform(Matrix.Translation(-origin))
for ro in rotor_objs: ro.location -= origin
rec['origin_shift'] = [round(x, 4) for x in origin]
def sh(v): return Vector(v) - origin

# lens cap: shallow emissive dome over the eye glass, facing the eye normal
e_c = sh(rec['eye']['centre']); radius = LENS_R if LENS_R > 0 else rec['eye']['glass_radius']
bmc = bmesh.new(); uvc_ = bmc.loops.layers.uv.new('UVMap')
seg, rings, depth = 28, 6, radius * .35
vs = [bmc.verts.new((0, 0, 0))]; uvs_ = [(0.5, 0.5)]
for r in range(1, rings + 1):
    f = r / rings
    for k in range(seg):
        a = k * 2 * math.pi / seg
        vs.append(bmc.verts.new((math.cos(a) * radius * f, math.sin(a) * radius * f, -depth * f * f))); uvs_.append((.5 + .5 * f * math.cos(a), .5 + .5 * f * math.sin(a)))
def face(ids):
    fc = bmc.faces.new([vs[i] for i in ids])
    for l, i in zip(fc.loops, ids): l[uvc_].uv = uvs_[i]
for k in range(seg): face([0, 1 + k, 1 + (k + 1) % seg])
for r in range(1, rings):
    for k in range(seg):
        a0 = 1 + (r - 1) * seg + k; a1 = 1 + (r - 1) * seg + (k + 1) % seg
        face([a0, a0 + seg, a1 + seg, a1])
capme = bpy.data.meshes.new('FeralLancer_LensCap'); bmc.to_mesh(capme); bmc.free()
capme.polygons.foreach_set('use_smooth', [True] * len(capme.polygons))
lm = bpy.data.materials.new('FeralLancer_Lens'); capme.materials.append(lm)
cap = bpy.data.objects.new('Lens cap', capme); s.collection.objects.link(cap)
cap.rotation_mode = 'QUATERNION'; cap.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(nrm)
# sit the dome's rim on the glass: push it out until no body vertex within the radius is in front of it
near = co[np.linalg.norm(co - np.array(sh(rec['eye']['centre'])), axis=1) < radius * .8]
proud = max(.004, float(((near - np.array(sh(rec['eye']['centre']))) @ np.array(nrm)).max()) + .002) if len(near) else .006
cap.location = e_c + nrm * proud
rec['lens_cap'] = dict(position=[round(x, 4) for x in cap.location], radius=round(radius, 4), normal=[round(x, 3) for x in nrm], proud_of_glass=round(proud, 4))
mzl = bpy.data.objects.new('Muzzle', None); s.collection.objects.link(mzl)
mzl.location = sh((rec['muzzle']['bore_centre_xz'][0], rec['muzzle']['tip_y'] - .01, rec['muzzle']['bore_centre_xz'][1]))
rec['muzzle']['position_blender'] = [round(x, 4) for x in mzl.location]
rec['muzzle']['position_gltf'] = [round(mzl.location.x, 4), round(mzl.location.z, 4), round(-mzl.location.y, 4)]
root = bpy.data.objects.new('FeralLancer', None); s.collection.objects.link(root)
obj.name = 'Body'; me.name = 'FeralLancer_Body'
for o in [obj] + rotor_objs + [cap, mzl]: o.parent = root
co = verts(); rec['body_bounds'] = dict(min=co.min(0).round(4).tolist(), max=co.max(0).round(4).tolist(), size=(co.max(0) - co.min(0)).round(4).tolist())
rec['body_triangles'] = sum(len(p.vertices) - 2 for p in me.polygons)
rec['rotor_order_note'] = 'diagonal pairs A/D and B/C share a spin direction; FeralDroid alternates by index, so assign rotors = [A, B, D, C]'

bpy.ops.object.select_all(action='DESELECT')
for o in [root] + root.children_recursive: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT / 'FeralLancer.glb'), export_format='GLB', use_selection=True,
                          export_image_format='NONE', export_yup=True, export_apply=False, export_animations=False)

# ------------------------------------------------------------------ renders
s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'; s.cycles.samples = 20; s.cycles.use_denoising = True
s.view_settings.view_transform = 'AgX'
wd = bpy.data.worlds.new('w'); s.world = wd; wd.use_nodes = True
wd.node_tree.nodes['Background'].inputs[0].default_value = (.62, .6, .56, 1); wd.node_tree.nodes['Background'].inputs[1].default_value = .8
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); s.collection.objects.link(sun)
sun.data.energy = 3.0; sun.rotation_euler = (math.radians(40), 0, math.radians(-35))
root.location = (0, 0, 2.2)
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, 0))
gm = bpy.data.materials.new('ground'); gm.use_nodes = True; gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.5, .42, .32, 1)
bpy.context.object.data.materials.append(gm)
# 1.8 m human marker
mk = bpy.data.materials.new('marker'); mk.use_nodes = True; mk.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.15, .35, .8, 1)
for kind, loc, sc in [('c', (1.6, .8, .45), (.07, .07, .45)), ('c', (1.8, .8, .45), (.07, .07, .45)), ('c', (1.7, .8, 1.17), (.19, .12, .3)), ('s', (1.7, .8, 1.68), (.11, .11, .12))]:
    (bpy.ops.mesh.primitive_cylinder_add if kind == 'c' else bpy.ops.mesh.primitive_uv_sphere_add)(location=loc); o = bpy.context.object; o.scale = sc; o.data.materials.append(mk)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); s.collection.objects.link(cam); s.camera = cam
lm.use_nodes = True; bsdf = lm.node_tree.nodes['Principled BSDF']
bsdf.inputs['Base Color'].default_value = (.2, .03, .02, 1); bsdf.inputs['Emission Color'].default_value = (1, .35, .08, 1); bsdf.inputs['Emission Strength'].default_value = 8
def shoot(name, target, dist, yaw, pitch, lens=50, res=(900, 700)):
    cam.data.lens = lens; cam.data.sensor_fit = 'VERTICAL'; cam.data.sensor_height = 24; s.render.resolution_x, s.render.resolution_y = res
    t = Vector(target); y = math.radians(yaw); p = math.radians(pitch)
    cam.location = t + Vector((math.sin(y) * math.cos(p) * dist, -math.cos(y) * math.cos(p) * dist, math.sin(p) * dist))
    cam.rotation_euler = (t - cam.location).to_track_quat('-Z', 'Y').to_euler()
    s.render.filepath = str(REN / f'{name}.png'); bpy.ops.render.render(write_still=True)
def game(name, dist, yaw, pitch):
    crop = 480; lens = 12 / math.tan(math.radians(30)) * 1080 / crop
    shoot(name, (0, 0, 2.2), dist, yaw, pitch, lens=lens, res=(crop, crop))
C0 = (0, 0, 2.2)
shoot('proc_front', C0, 4.2, 0, 6); shoot('proc_threequarter', C0, 4.4, 35, 18); shoot('proc_side', C0, 4.4, -90, 4)
shoot('proc_top', C0, 4.2, 0.01, 89); shoot('proc_under', C0, 3.8, 20, -35); shoot('proc_rear', C0, 4.4, 160, 15)
shoot('proc_eye', tuple(cap.matrix_world.translation), .9, 12, 6, lens=60, res=(700, 700))
shoot('proc_muzzle', tuple(mzl.matrix_world.translation), 1.0, 30, 10, lens=50, res=(700, 700))
shoot('proc_hull_top', (0, -.35, 2.45), 1.3, 10, 60, lens=50, res=(800, 700))
dA = rotor_objs[0]; shoot('proc_rotor_close', tuple(dA.matrix_world.translation), 1.2, 30, 55, lens=50, res=(700, 700))
shoot('proc_rotor_under', tuple(dA.matrix_world.translation), 1.2, 30, -45, lens=50, res=(700, 700))
for ro in rotor_objs: ro.location.z += .3
shoot('proc_exploded', C0, 4.2, 25, 35)
for ro in rotor_objs: ro.location.z -= .3
for ro in rotor_objs: ro.rotation_mode = 'XYZ'; ro.rotation_euler.z = math.radians(50)
shoot('proc_rotors_spun50', C0, 4.2, 0.01, 89)
for ro in rotor_objs: ro.rotation_euler.z = 0
game('proc_game25m', 25, 15, 4); game('proc_game35m', 35, -40, 2)
(OUT / 'lancer.json').write_text(json.dumps(rec, indent=1, default=float)); print('LANCER DONE')
