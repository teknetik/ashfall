"""Hero armour: fingerless gloves re-fitted to the new, bigger hands.
The shipped gloves (art/tutorial_set_20261002/blender/fit_gloves.py) are a shell cut from the OLD body's hands, 2.8 mm
off the skin, textured by a Meshy retexture on the old hand UVs. The new body is a different mesh with other UVs, so a
shell cut from it could not carry that texture. Instead the shipped shell itself (same vertices, faces and UVs, so its
material and textures stay as they are) is carried over to the new hands:
  1. every hand and finger bone gets an anatomical frame on both rigs (joint to joint, palm normal from the knuckles);
     the shell is re-posed bone by bone from the old frames to the new ones with its old skin weights, each segment
     scaled to the new joint spacing and finger thickness;
  2. each vertex is then laid `off` mm above the new skin of its OWN finger (straight out from the finger's centre
     line; nearest point on the palm), so fingers that stand close together cannot swap; between two close fingers
     the shell stops half-way; faces that still dip to the skin between their corners are lifted;
  3. weights are read from the new body at that same point (Hand + the finger joints, forearm at the cuff), so the
     shell bends exactly like the skin under it.
Usage: blender.sh fit_gloves.py -- [off=0.0035] [finger=1.0] [thumb=1.0]        -> work/stage/TS_Gloves.glb"""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/hero_base_20261120/armour/blender')
import bpy, bmesh, json, math
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
import hlib as H
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []; opt = dict(a.split('=', 1) for a in args if '=' in a)
OFF = float(opt.get('off', 0.0035)); CUFF = float(opt.get('cuff', 1.0)); MINFACE = float(opt.get('minface', 0.0012))
FINGER = float(opt.get('finger', 1.0)); THUMB = float(opt.get('thumb', 1.0))      # extra length of the finger / thumb sleeves
DIGITS = ('thumb', 'index', 'middle', 'ring', 'pinky')
rec = {'off': OFF}

arm, body = H.load_hero()
objs = H.import_glb(H.TS_OLD / 'TS_Gloves.glb')
g = next(o for o in objs if o.type == 'MESH'); oa = next(o for o in objs if o.type == 'ARMATURE'); H.rest(oa)
for m in list(g.modifiers): g.modifiers.remove(m)
mw = g.matrix_world.copy(); g.parent = None; g.matrix_world = mw
bpy.ops.object.select_all(action='DESELECT'); g.select_set(True); bpy.context.view_layer.objects.active = g
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
gname = {x.index: x.name for x in g.vertex_groups}
oldw = [{gname[e.group]: e.weight for e in v.groups if e.weight > 1e-4} for v in g.data.vertices]
P0 = [v.co.copy() for v in g.data.vertices]


def side_of(name): return 'l' if (name.startswith('Left') or name.endswith('_l')) else 'r'
def chain_of(name):
    for d in DIGITS:
        if name.startswith(d + '_'): return d
    return 'palm'


def joints(a, s):
    S = 'Left' if s == 'l' else 'Right'
    Hd = H.bone_head(a, S + 'Hand'); E = H.bone_head(a, S + 'ForeArm')
    J = {d: [H.bone_head(a, f'{d}_0{k}_{s}') for k in (1, 2, 3)] + [H.bone_tail(a, f'{d}_03_{s}')] for d in DIGITS}
    ax = (J['middle'][0] - Hd).normalized()
    k = J['index'][0] - J['pinky'][0]; k = (k - ax * k.dot(ax)).normalized()
    return dict(S=S, H=Hd, E=E, J=J, a=ax, k=k, n=ax.cross(k), span=(J['index'][0] - J['pinky'][0]).length, palm=(J['middle'][0] - Hd).length)


def frame(o, y, n):
    y = y.normalized(); z = (n - y * n.dot(y)).normalized(); x = y.cross(z)
    m = Matrix((x, y, z)).transposed().to_4x4(); m.translation = o; return m


def radial(points, o, y):
    rs = sorted(((p - o) - y * (p - o).dot(y)).length for p in points)
    return rs[len(rs) // 2] if rs else None


# body vertex weights by name (new body)
bname = {x.index: x.name for x in body.vertex_groups}
bw = [{bname[e.group]: e.weight for e in v.groups if e.weight > 1e-4} for v in body.data.vertices]
BW = [body.matrix_world @ v.co for v in body.data.vertices]

def centroid_offset(points, F):
    """Mean position of `points` across the bone (x, z of frame F): where the flesh sits relative to the joint line."""
    if not points: return Vector((0, 0, 0))
    inv = F.inverted(); loc = [inv @ p for p in points]
    return Vector((sum(q.x for q in loc) / len(loc), 0.0, sum(q.z for q in loc) / len(loc)))


M = {}; scales = {}; AXIS = {}
for s in 'lr':
    jo = joints(oa, s); jn = joints(arm, s); S = jo['S']
    # palm
    sy = jn['palm'] / jo['palm']; sx = jn['span'] / jo['span']
    po = [P0[i] for i in range(len(P0)) if oldw[i].get(S + 'Hand', 0) > 0.6]
    pn = [BW[i] for i in range(len(BW)) if bw[i].get(S + 'Hand', 0) > 0.6]
    Fo = frame(jo['H'], jo['a'], jo['n']); Fn = frame(jn['H'], jn['a'], jn['n'])
    to = sorted(abs((p - jo['H']).dot(jo['n'])) for p in po); tn = sorted(abs((p - jn['H']).dot(jn['n'])) for p in pn)
    sz = max(0.8, min(1.8, tn[int(len(tn) * .8)] / max(1e-4, to[int(len(to) * .8)] - 0.0028)))
    co = centroid_offset(po, Fo); cn = centroid_offset(pn, Fn); co.x = cn.x = 0.0          # thickness direction only
    M[S + 'Hand'] = Fn @ Matrix.Translation(cn) @ Matrix.Diagonal((sx, sy, sz, 1)) @ Matrix.Translation(-co) @ Fo.inverted()
    scales[S + 'Hand'] = (round(sx, 3), round(sy, 3), round(sz, 3))
    # cuff (forearm end)
    yo = (jo['H'] - jo['E']).normalized(); yn = (jn['H'] - jn['E']).normalized()
    Fo = frame(jo['H'], yo, jo['n']); Fn = frame(jn['H'], yn, jn['n'])
    po = [P0[i] for i in range(len(P0)) if oldw[i].get(S + 'ForeArm', 0) > 0.5]
    pn = [BW[i] for i in range(len(BW)) if bw[i].get(S + 'ForeArm', 0) > 0.3 and -0.05 < (BW[i] - jn['H']).dot(yn) < 0.0]
    co = centroid_offset(po, Fo); cn = centroid_offset(pn, Fn)
    ro = radial(po, Fo @ co, yo); rn = radial(pn, Fn @ cn, yn)
    sr = max(0.8, min(1.8, rn / max(1e-4, ro - 0.0028))) if ro and rn else sx
    M[S + 'ForeArm'] = Fn @ Matrix.Translation(cn) @ Matrix.Diagonal((sr, CUFF, sr, 1)) @ Matrix.Translation(-co) @ Fo.inverted()
    scales[S + 'ForeArm'] = (round(sr, 3), CUFF, round(sr, 3))
    for d in DIGITS:
        for k in (1, 2, 3):
            b = f'{d}_0{k}_{s}'
            o0, o1 = jo['J'][d][k - 1], jo['J'][d][k]; n0, n1 = jn['J'][d][k - 1], jn['J'][d][k]
            Fo = frame(o0, o1 - o0, jo['n']); Fn = frame(n0, n1 - n0, jn['n'])
            po = [P0[i] for i in range(len(P0)) if oldw[i].get(b, 0) > 0.5]
            pn = [BW[i] for i in range(len(BW)) if bw[i].get(b, 0) > 0.5]
            co = centroid_offset(po, Fo); cn = centroid_offset(pn, Fn)
            ro = radial(po, Fo @ co, (o1 - o0).normalized()); rn = radial(pn, Fn @ cn, (n1 - n0).normalized())
            sr = max(0.8, min(1.8, rn / max(1e-4, ro - 0.0028))) if ro and rn else 1.2
            sl = (n1 - n0).length / (o1 - o0).length * (FINGER if d != 'thumb' else THUMB)
            if d == 'thumb' and k == 1:                                       # the thumb's first joint lies inside the palm
                co = cn = Vector((0, 0, 0)); sr = scales[S + 'Hand'][0]
            M[b] = Fn @ Matrix.Translation(cn) @ Matrix.Diagonal((sr, sl, sr, 1)) @ Matrix.Translation(-co) @ Fo.inverted()
            AXIS[b] = (Fn @ cn, (n1 - n0).normalized())                      # the finger's own centre line there
            scales[b] = (round(sr, 3), round(sl, 3), round(cn.length * 1000, 1))
rec['scales'] = scales

# ---- 1. re-pose the shell from the old frames to the new ones (linear blend with the old weights)
P1 = []
for p, ws in zip(P0, oldw):
    acc = Vector(); tot = 0.0
    for nme, w in ws.items():
        if nme in M: acc += (M[nme] @ p) * w; tot += w
    P1.append(acc / tot if tot > 0 else p.copy())

# ---- per finger / palm surfaces of the new hands
bm = bmesh.new(); bm.from_mesh(body.data); bmesh.ops.triangulate(bm, faces=bm.faces[:]); bm.verts.ensure_lookup_table()
HANDSET = {s: {S + 'Hand', S + 'ForeArm'} | {f'{d}_0{k}_{s}' for d in DIGITS for k in (1, 2, 3)} for s, S in (('l', 'Left'), ('r', 'Right'))}
surf = {}
for fc in bm.faces:
    vi = [v.index for v in fc.verts]
    tot = {}
    for i in vi:
        for nme, w in bw[i].items():
            for s in 'lr':
                if nme in HANDSET[s]: tot[(s, chain_of(nme))] = tot.get((s, chain_of(nme)), 0) + w
    if not tot or sum(tot.values()) < 1.5: continue
    key = max(tot, key=tot.get)
    if key[1] == 'palm':
        S = 'Left' if key[0] == 'l' else 'Right'; hd = H.bone_head(arm, S + 'Hand')
        if min((BW[i] - hd).length for i in vi) > 0.11: continue           # forearm far above the wrist
    surf.setdefault(key, []).append(tuple(vi))
bm.free()
bvh = {k: BVHTree.FromPolygons(BW, v) for k, v in surf.items()}
rec['surface_tris'] = {f'{k[0]}_{k[1]}': len(v) for k, v in surf.items()}


def nearest(p, s, ch, reach=0.05):
    keys = [(s, ch), (s, 'palm')] if ch != 'palm' else [(s, c) for c in DIGITS + ('palm',)]
    best = None
    for k in keys:
        if k not in bvh: continue
        hit = bvh[k].find_nearest(p, reach)
        if hit[0] is None: continue
        if best is None or hit[3] < best[0]: best = (hit[3], hit[0], hit[1], k, hit[2])
    return best


def radial_hit(p, s, ch, bone):
    """From the finger's centre line straight out through p: where the ray leaves that finger's own skin (keeps the
    shell's vertices spread round the finger; a nearest-point search bunches them on the near side)."""
    a, y = AXIS[bone]; q = a + y * (p - a).dot(y); r = p - q
    if r.length < 1e-5: return None
    r.normalize()
    hit = bvh[(s, ch)].ray_cast(q, r, 0.03)
    if hit[0] is None or hit[1].dot(r) < 0.25: return None                 # no exit, grazing, or the centre line is outside
    return (hit[3], hit[0], hit[1], (s, ch), hit[2])


dom = []; dbone = []
for ws in oldw:
    nme = max(ws, key=ws.get); dom.append((side_of(nme), chain_of(nme)))
    fb = {k: w for k, w in ws.items() if chain_of(k) != 'palm'}
    best = max(fb, key=fb.get) if fb and sum(fb.values()) > 0.75 else None               # clearly on a finger
    dbone.append(best if best and not best.startswith('thumb_01') else None)             # thumb_01 lies inside the palm

# ---- 2. lay the shell OFF above the new skin; between two fingers that stand close, half-way at most
def other_skin(loc, nrm, s, own):
    t = None
    for c in DIGITS + ('palm',):
        if c == own[1] or (s, c) not in bvh: continue
        hit = bvh[(s, c)].ray_cast(loc + nrm * 2e-4, nrm, 2 * OFF + 0.002)
        if hit[0] is not None and hit[1].dot(nrm) < 0 and (t is None or hit[3] < t): t = hit[3]
    return t


final = []; W = []; far = []; missed = 0; byray = 0; NRM = []; SQ = []
for i, (p, (s, ch)) in enumerate(zip(P1, dom)):
    b = radial_hit(p, s, ch, dbone[i]) if dbone[i] else None
    if b is not None: byray += 1
    else: b = nearest(p, s, ch)
    if b is None:
        final.append(p); W.append(None); NRM.append(Vector()); SQ.append(True); missed += 1; continue
    dist, loc, nrm, k, ti = b
    off = OFF; t = other_skin(loc, nrm, s, k); sq = t is not None and t < 2 * OFF
    if sq: off = max(0.0004, 0.45 * t)
    # never inside (or touching) another finger's skin: fingers that touch leave no room for leather between them
    for _ in range(4):
        q = loc + nrm * off; bad = False
        for c in DIGITS + ('palm',):
            if c == k[1] or (s, c) not in bvh: continue
            h2 = bvh[(s, c)].find_nearest(q, 0.01)
            if h2[0] is not None and (q - h2[0]).dot(h2[1]) < 0.0004: bad = True; break
        if not bad: break
        off = max(0.0003, off * 0.5); sq = True
    final.append(loc + nrm * off); far.append((p - loc).length); NRM.append(nrm); SQ.append(sq)
    # ---- 3. weights from the new body at the same point (barycentric on the hit triangle)
    i0, i1, i2 = surf[k][ti]; a, bb, cc = BW[i0], BW[i1], BW[i2]
    v0 = bb - a; v1 = cc - a; v2 = loc - a
    d00 = v0.dot(v0); d01 = v0.dot(v1); d11 = v1.dot(v1); d20 = v2.dot(v0); d21 = v2.dot(v1); den = d00 * d11 - d01 * d01
    if abs(den) < 1e-14: bc = (1 / 3, 1 / 3, 1 / 3)
    else:
        v = (d11 * d20 - d01 * d21) / den; w = (d00 * d21 - d01 * d20) / den; bc = (max(0, 1 - v - w), max(0, v), max(0, w))
    ws = {}
    for idx, t_ in zip((i0, i1, i2), bc):
        for nme, wt in bw[idx].items():
            if nme in HANDSET[s]: ws[nme] = ws.get(nme, 0) + wt * t_
    top = sorted(ws.items(), key=lambda kv: -kv[1])[:4]; tot = sum(w for _, w in top)
    W.append({n: w / tot for n, w in top} if tot > 1e-6 else None)
# duplicates at UV seams must stay welded: same position and weights for the whole group
key = {}; grp = []
for i, p in enumerate(P0):
    kk = (round(p.x, 5), round(p.y, 5), round(p.z, 5)); grp.append(key.setdefault(kk, len(key)))
gp = {}; gw = {}; gn = {}; gs = {}
for i, p in enumerate(final):
    gp.setdefault(grp[i], p); gw.setdefault(grp[i], W[i]); gn.setdefault(grp[i], NRM[i]); gs.setdefault(grp[i], SQ[i])
for i in range(len(final)): final[i] = gp[grp[i]]; W[i] = gw[grp[i]]
for v, p in zip(g.data.vertices, final): v.co = p
g.data.update()

# ---- the shell is coarser than the skin: where a face still dips to the skin between its corners, lift the corners
#      along their own skin normals (at most LIFTMAX in total; not between two close fingers)
allb = {s: BVHTree.FromPolygons(BW, [t for c in DIGITS + ('palm',) for t in surf.get((s, c), [])]) for s in 'lr'}
lift = {}; LIFTMAX = 0.0025
for it in range(5):
    g.data.update(); need = {}
    for poly in g.data.polygons:
        vs = list(poly.vertices); s = dom[vs[0]][0]
        pts = [g.data.vertices[i].co for i in vs]
        samples = [sum(pts, Vector()) / len(pts)] + [(pts[j] + pts[(j + 1) % len(pts)]) / 2 for j in range(len(pts))]
        worst = None
        for q in samples:
            hit = allb[s].find_nearest(q, 0.02)
            if hit[0] is None: continue
            sd = (q - hit[0]).dot(hit[1])
            if sd < MINFACE and (worst is None or sd < worst): worst = sd
        if worst is not None:
            for i in vs:
                if not gs[grp[i]]: need[grp[i]] = max(need.get(grp[i], 0.0), (MINFACE - worst) * 1.2)
    if not need: break
    for k_, d in need.items(): lift[k_] = min(LIFTMAX, lift.get(k_, 0.0) + d)
    for i, v in enumerate(g.data.vertices):
        if grp[i] in lift: v.co = gp[grp[i]] + gn[grp[i]] * lift[grp[i]]
g.data.update(); squeezed = sum(1 for k_ in gs if gs[k_]); lifted = len(lift)
far.sort(); rec.update(missed=missed, by_ray=byray, squeezed_between_fingers=squeezed, faces_lifted_groups=lifted,
                       reposed_to_skin_mm={'p50': round(far[len(far) // 2] * 1000, 1), 'p95': round(far[int(len(far) * .95)] * 1000, 1), 'max': round(far[-1] * 1000, 1)})

g.vertex_groups.clear(); fallback = 0
for i, ws in enumerate(W):
    if ws is None:
        s = dom[i][0]; ws = {('Left' if s == 'l' else 'Right') + 'Hand': 1.0}; fallback += 1
    for nme, w in ws.items():
        (g.vertex_groups.get(nme) or g.vertex_groups.new(name=nme)).add([i], w, 'REPLACE')
rec['fallback_weights'] = fallback
for o in objs:
    if o.type == 'ARMATURE': bpy.data.objects.remove(o, do_unlink=True)
g.name = 'TS_Gloves'; g.data.name = 'TS_Gloves'
H.smooth_shade(g, 60)
g.data.materials.clear()
H.bind(g, arm)
rec.update(gap=H.gap_stats(g, body), pen=H.penetration(g, body), tris=H.tris(g), verts=len(g.data.vertices))
H.log('FIT gloves', json.dumps(rec)); (H.WORK / 'gloves_fit.json').write_text(json.dumps(rec, indent=1))
(H.WORK / 'stage').mkdir(exist_ok=True)
H.export_skinned(g, arm, H.WORK / 'stage' / 'TS_Gloves.glb')
