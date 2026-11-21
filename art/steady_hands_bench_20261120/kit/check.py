# kit/check.py: the checks of ANYMACHINE.md section 3, run on a family's export/. Writes export/check.json and exits
# non-zero when a check fails. A family's own check.py is three lines:
#
#   import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'kit'))
#   import kitload; check = kitload.load('check')      # by file: "import check" can find another family's check.py
#   check.main(os.path.dirname(os.path.abspath(__file__)), externals=[('../pistol', None)])     # externals optional
#
# Run: SH/blender.sh <family>/check.py          (seconds; no bake needed, a --nobake build is enough)
#
# 1. contract      names, kinds, parents, helper empties, budget (contract.validate).
# 2. params        every 0-1 parameter in 50 steps: triangle overlaps of the parts on that bone against every part
#                  not on it, minimum clearance, and that values outside 0-1 clamp.
# 3. sequence      the assembly path sweep: every remove / insert event of contract.sequence, the part moved between
#                  its rest pose and its '__clear' pose in 40 steps against every part that is there at that point.
#                  No overlap anywhere on the path; contacts at the seated end are listed and anything unexpected is
#                  reported. A removal sweep is the insertion run backwards, so both directions are covered.
#                  A part of ANOTHER family that seats on this one is swept between two pose marks (event fields
#                  'seat' and 'clear'), and then rides the part that owns the mark; 'unit' brings its riders with it;
#                  'among' limits what is in the way to the named families (see contract.sequence).
#
# Other families: externals=[(dir, ids, 'absent')]: ids = which of its parts to load (None: all, in the state its own
# sequence leaves it in); 'absent' = they are not in place when this family's sequence starts (it inserts them).
# Stand-ins: a mesh in this family's own .blend that is registered with another family's id (contract.part(o,
# 'materials', 'sheet_a_plate', ...)) is not exported and not listed in parts.json; the check treats it as a part of
# that family that starts absent.
# 4. fasteners     every fastener's axis passes through a hole in everything it holds and its seated head touches.
# 5. export        the GLB re-imported into an empty scene: nodes, triangles, bounds, helper empties, clips and
#                  their length, and each parameter's end pose against the driven rig.
#
# Overlap test: the moving part is shrunk by SHRINK (0.03 mm) along its normals first, so faces that merely touch do
# not count and anything deeper does. "Contact" is a gap under CONTACT (0.30 mm).
import bpy, bmesh, sys, os, json, math, time
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

KIT = os.path.dirname(os.path.abspath(__file__))
if KIT not in sys.path:
    sys.path.insert(0, KIT)
import contract as CT
import rig as RG
import bake as BK

EXT_GONE = set()      # parts of external families that are off at the start (see load_external)
PLACED = {}           # id -> world pose of a part the sequence seated on a pose mark (filled by check_sequence)
SHRINK = 0.00003
CONTACT = 0.00030
STEPS_SEQ = 40
STEPS_PARAM = 50


# ---------------------------------------------------------------------- geometry access
class Geo:
    """A part's triangles in its own space (plain, and shrunk along the normals)."""
    def __init__(self, o):
        dg = bpy.context.evaluated_depsgraph_get()
        oe = o.evaluated_get(dg)
        me = oe.to_mesh()
        me.calc_loop_triangles()
        self.v = [v.co.copy() for v in me.vertices]
        self.vs = [v.co - v.normal * SHRINK for v in me.vertices]
        self.t = [tuple(t.vertices) for t in me.loop_triangles]
        oe.to_mesh_clear()
        self.name = o.name

    def world(self, M, shrunk=False):
        src = self.vs if shrunk else self.v
        return [M @ p for p in src]

    def bvh(self, M, shrunk=False):
        return BVHTree.FromPolygons(self.world(M, shrunk), self.t, all_triangles=True)

    def samples(self, M):
        w = self.world(M)
        return w + [(w[a] + w[b] + w[c]) / 3 for a, b, c in self.t]

    def aabb(self, M):
        a = np.array([tuple(p) for p in self.world(M)])
        return a.min(0), a.max(0)


def world_matrix(o):
    bpy.context.view_layer.update()
    return o.evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world.copy()


def lerp_pose(A, B, t):
    la, ra, sa = A.decompose(); lb, rb, sb = B.decompose()
    return Matrix.LocRotScale(la.lerp(lb, t), ra.slerp(rb, t), sa)


def inside(tree, p):
    """Is a point inside a closed mesh (three rays vote on parity)."""
    votes = 0
    for d in ((0.013, 1, 0.021), (0.017, -0.011, 1), (1, 0.02, 0.013)):
        d = Vector(d).normalized(); q = Vector(p); hits = 0
        for _ in range(64):
            h = tree.ray_cast(q, d, 10.0)
            if h[0] is None:
                break
            hits += 1; q = h[0] + d * 1e-6
        votes += hits % 2
    return votes >= 2


# ---------------------------------------------------------------------- 2. parameters
def check_params(P, G, res):
    sc = bpy.context.scene
    arm = bpy.data.objects.get(sc.get('sh_rig', ''))
    joints = json.loads(sc.get('sh_joints', '[]'))
    absent = set(json.loads(sc.get('sh_absent', '[]')))
    out = {'ok': True, 'params': {}}
    if not arm or not joints:
        out['note'] = 'no rig'
        res['params'] = out
        return True
    ends = {}
    by_name = {o.name: fid for fid, o in P.items()}

    def bones_below(b):
        r = [b]
        for j in joints:
            if j['parent_bone'] == b:
                r += bones_below(j['bone'])
        return r
    for j in joints:
        zero = {k['param']: float(k.get('rest', 0.0)) for k in joints if not k['continuous']}      # every other joint at its rest
        if j['continuous']:
            out['params'][j['param']] = {'type': 'continuous', 'note': 'code-driven, not swept'}
            continue
        base = dict(zero); base.update(j.get('requires') or {})
        below = bones_below(j['bone'])
        moving = [o for o in P.values() if o.parent is arm and o.parent_type == 'BONE' and o.parent_bone in below]
        fixed = [o for fid, o in P.items() if o not in moving and fid not in absent]
        RG.set_params(arm, base)
        fixed_bvh = {o.name: G[o.name].bvh(world_matrix(o)) for o in fixed}
        rows, worst = [], None
        rest_pairs = None
        for i in range(STEPS_PARAM + 1):
            v = dict(base); v[j['param']] = i / STEPS_PARAM
            RG.set_params(arm, v)
            hits = {}
            clear = 1.0
            for o in moving:
                M = world_matrix(o)
                mb = G[o.name].bvh(M, shrunk=True)
                sm = G[o.name].samples(M)
                lo, hi = G[o.name].aabb(M)
                for fo in fixed:
                    flo, fhi = G[fo.name].aabb(world_matrix(fo))
                    if np.any(lo > fhi + 0.004) or np.any(hi < flo - 0.004):
                        continue
                    n = len(fixed_bvh[fo.name].overlap(mb))
                    if n:
                        hits['%s x %s' % (by_name[o.name], by_name[fo.name])] = n
                    for p in sm:
                        nn = fixed_bvh[fo.name].find_nearest(p, 0.004)
                        if nn[0] is not None:
                            clear = min(clear, nn[3])
            if i == 0:
                rest_pairs = dict(hits)
            new = {k: n for k, n in hits.items() if k not in (rest_pairs or {})}
            rows.append({'v': round(i / STEPS_PARAM, 3), 'overlaps': hits, 'new': new, 'min_clearance_mm': round(clear * 1000, 3) if clear < 1 else None})
        # end pose of every moving part (for the export check) and clamping
        v = dict(base); v[j['param']] = 1.0
        RG.set_params(arm, v)
        ends[j['param']] = {o.name: [round(x, 6) for x in world_matrix(o).translation] for o in moving}
        end_m = {o.name: world_matrix(o) for o in moving}
        v[j['param']] = 1.6
        RG.set_params(arm, v)
        over = max([(world_matrix(o).translation - end_m[o.name].translation).length for o in moving] + [0.0])
        v[j['param']] = -0.5
        RG.set_params(arm, v)
        v0 = dict(base); v0[j['param']] = 0.0          # against the pose AT 0, not the rest pose (a param may rest at 0.5)
        under_m = {o.name: world_matrix(o) for o in moving}
        RG.set_params(arm, v0)
        under = max([(world_matrix(o).translation - under_m[o.name].translation).length for o in moving] + [0.0])
        bad_steps = [r['v'] for r in rows if r['new']]
        rest_over = rows[0]['overlaps']
        cl = [r['min_clearance_mm'] for r in rows if r['min_clearance_mm'] is not None]
        ok = not bad_steps and not rest_over and over < 1e-5 and under < 1e-5 and bool(moving)
        out['params'][j['param']] = {'ok': ok, 'type': j['type'], 'min': j['min'], 'max': j['max'], 'unit': j['unit'],
                                     'moving': [by_name[o.name] for o in moving], 'with': j.get('requires') or {},
                                     'steps': len(rows), 'overlap_at_rest': rest_over, 'steps_with_new_overlap': bad_steps,
                                     'first_new_overlap': next((r['new'] for r in rows if r['new']), None),
                                     'min_clearance_mm': min(cl) if cl else None,
                                     'clamp_error_mm': [round(over * 1000, 4), round(under * 1000, 4)]}
        if not moving:
            out['params'][j['param']]['note'] = 'no part rides this bone'
        out['ok'] = out['ok'] and ok
    RG.set_params(arm, {k['param']: float(k.get('rest', 0.0)) for k in joints if not k['continuous']})
    res['params'] = out
    res['_ends'] = ends
    return out['ok']


# ---------------------------------------------------------------------- 3. sequence
def check_sequence(P, G, res, ext):
    sc = bpy.context.scene
    arm = bpy.data.objects.get(sc.get('sh_rig', ''))
    joints = json.loads(sc.get('sh_joints', '[]'))
    events = json.loads(sc.get('sh_sequence', '[]'))
    absent = set(json.loads(sc.get('sh_absent', '[]')))
    allp = dict(P); allp.update(ext)
    D = {fid: json.loads(o['sh']) for fid, o in allp.items()}
    present = {fid for fid in allp if fid not in absent and fid not in EXT_GONE}
    out = {'ok': True, 'events': [], 'never_moved': []}
    placed = PLACED    # id -> world pose, for parts seated on a pose mark (they are not there in their own .blend)
    placed.clear()
    carried = {}       # id -> the part it rides since it was seated on that part's mark
    went_with = {}     # id -> what left with it when it was removed
    by_node = {o.name: fid for fid, o in allp.items()}

    def pose(fid):
        return placed[fid] if fid in placed else world_matrix(allp[fid])

    def par(fid):
        return carried.get(fid, D.get(fid, {}).get('parent'))
    if not events:
        out['note'] = 'no sequence declared'
        res['sequence'] = out
        return True
    zero = {k['param']: float(k.get('rest', 0.0)) for k in joints if not k['continuous']}

    def root_of(fid):
        seen = set()
        while fid in D and par(fid) and par(fid) in D and fid not in seen:
            seen.add(fid); fid = par(fid)
        return fid

    def children(fid, pres):
        r = []
        for c in D:
            if par(c) == fid and (pres is None or c in pres):
                r += [c] + children(c, pres)
        return r
    # group semantics: a removal is swept against the state at the start of its group, an insertion against the state
    # at the end of its group
    i = 0
    moved = set()
    while i < len(events):
        g = events[i].get('group')
        j = i + 1
        while g and j < len(events) and events[j].get('group') == g:
            j += 1
        grp = events[i:j]
        start = set(present)
        end = set(present)
        for e in grp:
            (end.discard if e['op'] == 'remove' else end.add)(e['part'])
            if e['op'] == 'remove':
                went_with[e['part']] = children(e['part'], start)
                for c in went_with[e['part']]:
                    end.discard(c)
            elif e.get('unit'):       # what rides it comes with it
                for c in (went_with[e['part']] if e['part'] in went_with else children(e['part'], None)):
                    end.add(c)
        for e in grp:
            fid = e['part']; moved.add(fid)
            row = {'step': e.get('step'), 'op': e['op'], 'part': fid, 'ok': True}
            o = allp.get(fid)
            if o is None:
                row.update(ok=False, error='unknown part'); out['events'].append(row); out['ok'] = False
                continue
            d = D.get(fid, {})
            if d.get('flex'):
                row['skipped'] = 'flexible part (peeled, snipped or bent off): not swept'
                out['events'].append(row)
                continue
            se = None
            if e.get('seat'):
                se = bpy.data.objects.get(e['seat']); ce = bpy.data.objects.get(e.get('clear', ''))
                if se is None or ce is None:
                    row.update(ok=False, error='pose mark %s or %s not found' % (e['seat'], e.get('clear'))); out['events'].append(row); out['ok'] = False
                    continue
            else:
                ce = bpy.data.objects.get(o.name + '__clear')
            if ce is None:
                row.update(ok=False, error='no __clear empty'); out['events'].append(row); out['ok'] = False
                continue
            if arm:
                v = dict(zero); v.update(e.get('params') or {})
                RG.set_params(arm, v)
            state = start if e['op'] == 'remove' else end
            riders = [c for c in children(fid, start | end)]
            # a flexible part that the moving part touches (its own lead, the tape over it) bends out of the way
            soft = {x for x in state if D.get(x, {}).get('flex') and (x in d.get('touches', []) or fid in D[x].get('touches', []))}
            # only what belongs to the same assembly is in the way: a loose thing lying elsewhere (a test card) is not
            own = pose(fid)
            rest_of = {c: pose(c) for c in riders}          # riders keep their place on the part: relative to its own pose
            Mri = own.inverted()
            if se is not None:
                Mr = world_matrix(se)
                owner = by_node.get(e['seat'].split('__')[0])
                row['seat'] = e['seat']; row['seat_owner'] = owner
                row['own_rest_to_seat_mm'] = round((own.translation - Mr.translation).length * 1000, 3)
                placed[fid] = Mr
                for c in riders:
                    placed[c] = Mr @ Mri @ rest_of[c]
                if owner:
                    carried[fid] = owner
            else:
                Mr = own
            Mc = world_matrix(ce)
            root = root_of(fid)
            # ... and so is anything of another family, except its loose things (they lie elsewhere on the bench)
            others = [x for x in state if x != fid and x not in riders and x not in soft and
                      (root_of(x) == root or ((x in ext or root in ext) and not D.get(x, {}).get('loose')))]
            if e.get('among'):
                others = [x for x in others if x.split('.')[0] in e['among']]
                row['among'] = e['among']
            # neighbours: anything whose box comes near the swept box
            lo = np.full(3, 1e9); hi = np.full(3, -1e9)
            for t in (0.0, 0.5, 1.0):
                M = lerp_pose(Mr, Mc, t)
                for nm, Mm in [(o.name, M)] + [(allp[c].name, M @ Mri @ rest_of[c]) for c in riders]:
                    a, b = G[nm].aabb(Mm)
                    lo = np.minimum(lo, a); hi = np.maximum(hi, b)
            near = []
            for x in others:
                ox = allp[x]
                a, b = G[ox.name].aabb(pose(x))
                if not (np.any(lo > b + 0.003) or np.any(hi < a - 0.003)):
                    near.append(x)
            trees = {x: G[allp[x].name].bvh(pose(x)) for x in near}
            hits_by_step = {}
            contacts = {}
            path_clear = 1.0
            for s in range(STEPS_SEQ + 1):
                t = s / STEPS_SEQ
                M = lerp_pose(Mr, Mc, t)
                for nm, Mm in [(o.name, M)] + [(allp[c].name, M @ Mri @ rest_of[c]) for c in riders]:
                    mb = G[nm].bvh(Mm, shrunk=True)
                    sm = G[nm].samples(Mm) if s in (0, STEPS_SEQ) or s % 4 == 0 else None
                    for x in near:
                        n = len(trees[x].overlap(mb))
                        if n:
                            hits_by_step.setdefault(s, {})[x] = hits_by_step.get(s, {}).get(x, 0) + n
                        if sm is not None:
                            dmin = 1.0
                            for p in sm:
                                nn = trees[x].find_nearest(p, 0.002)
                                if nn[0] is not None and nn[3] < dmin:
                                    dmin = nn[3]
                            if s == 0 and dmin < CONTACT:
                                contacts[x] = round(dmin * 1000, 3)
                            if s > 0:
                                path_clear = min(path_clear, dmin)
            expected = set(d.get('held_by', [])) | set(d.get('touches', [])) | ({d['parent']} if d.get('parent') else set())
            expected |= set(e.get('expect') or []) | ({carried[fid]} if fid in carried else set())
            for c in riders:                  # what rides it may touch what it declares too
                expected |= set(D.get(c, {}).get('touches', []))
            for x, dx in D.items():       # whatever it holds, and its own children, may touch it too
                if fid in dx.get('held_by', []) or dx.get('parent') == fid or fid in dx.get('touches', []):
                    expected.add(x)
                f = dx.get('fastener')
                if f and (fid in f['holds'] or f.get('into') == fid):
                    expected.add(x)
            f = d.get('fastener')
            if f:
                expected |= set(f['holds']) | ({f['into']} if f.get('into') else set())
            unexpected = sorted(set(contacts) - expected)
            row.update({'against': len(others), 'near': len(near), 'riders': riders, 'travel_mm': round((Mc.translation - Mr.translation).length * 1000, 2),
                        'overlap_steps': {str(k): v for k, v in sorted(hits_by_step.items())},
                        'contacts_seated_mm': contacts, 'unexpected_contacts': unexpected,
                        'min_clearance_on_path_mm': round(path_clear * 1000, 3) if path_clear < 1 else None})
            if hits_by_step:
                row['ok'] = False
                first = min(hits_by_step)
                row['error'] = 'passes through %s at step %d of %d' % (', '.join(sorted(hits_by_step[first])), first, STEPS_SEQ)
                out['ok'] = False
            if e.get('params'):
                row['with'] = e['params']
            out['events'].append(row)
        present = end
        i = j
    if arm:
        RG.set_params(arm, zero)
    for fid, d in D.items():
        if fid in P and d.get('parent') and not d.get('loose') and not d.get('fixed') and fid not in moved:
            out['never_moved'].append(fid)
    out['left_at_end'] = sorted(x for x in present if x in P)
    res['sequence'] = out
    return out['ok']


# ---------------------------------------------------------------------- 4. fasteners
def check_fasteners(P, G, res, ext):
    out = {'ok': True, 'fasteners': {}}
    allp = dict(P); allp.update(ext)
    for fid, o in P.items():
        d = json.loads(o['sh'])
        f = d.get('fastener')
        if not f:
            continue
        row = {'ok': True, 'holes': {}}
        ce = bpy.data.objects.get(o.name + '__clear')
        M = world_matrix(o)
        if ce is None:
            row.update(ok=False, error='no __clear empty'); out['fasteners'][fid] = row; out['ok'] = False
            continue
        ax = (world_matrix(ce).translation - M.translation)
        if ax.length < 1e-6:
            row.update(ok=False, error='__clear is at the rest pose'); out['fasteners'][fid] = row; out['ok'] = False
            continue
        ax.normalize()
        w = G[o.name].world(M)
        depth = max(0.0, -min((p - M.translation).dot(ax) for p in w))       # how far the shank goes in
        rs = (f.get('shank_mm') or 0) / 2000.0
        if not rs:      # estimate: the radius of the lower half of the screw
            low = [p for p in w if (p - M.translation).dot(ax) < -depth * 0.5]
            rs = max(((p - M.translation) - ax * (p - M.translation).dot(ax)).length for p in low) if low else 0.001
        targets = list(f['holds']) + ([f['into']] if f.get('into') else [])
        for x in targets:
            ox = allp.get(x)
            if ox is None:
                row['holes'][x] = {'ok': None, 'note': 'in another family, not loaded'}
                continue
            tree = G[ox.name].bvh(PLACED[x] if x in PLACED else world_matrix(ox))
            in_hole = solid = 0
            n = 48
            for k in range(n):
                p = M.translation - ax * (depth * (k + 0.5) / n)
                nn = tree.find_nearest(p, rs + 0.003)
                if nn[0] is None:
                    continue
                if inside(tree, p):
                    solid += 1
                elif nn[3] <= rs + 0.0012:
                    in_hole += 1
            ok = in_hole >= 2 and solid == 0
            row['holes'][x] = {'ok': ok, 'samples_in_hole': in_hole, 'samples_in_solid': solid}
            row['ok'] = row['ok'] and ok
        # the seated head touches the first thing it holds
        if f['holds'] and allp.get(f['holds'][0]) is not None:
            ox = allp[f['holds'][0]]
            tree = G[ox.name].bvh(PLACED[f['holds'][0]] if f['holds'][0] in PLACED else world_matrix(ox))
            dmin = 1.0
            for p in G[o.name].samples(M):
                nn = tree.find_nearest(p, 0.003)
                if nn[0] is not None and nn[3] < dmin:
                    dmin = nn[3]
            row['head_gap_mm'] = round(dmin * 1000, 3) if dmin < 1 else None
            if dmin > CONTACT:
                row['ok'] = False; row['error'] = 'head does not touch %s' % f['holds'][0]
        row['axis_depth_mm'] = round(depth * 1000, 2); row['shank_r_mm'] = round(rs * 1000, 2)
        out['fasteners'][fid] = row
        out['ok'] = out['ok'] and row['ok']
    res['fasteners'] = out
    return out['ok']


# ---------------------------------------------------------------------- 5. export
def check_export(family_dir, family, src, res):
    out = {'ok': True, 'problems': []}
    exp = os.path.join(family_dir, 'export')
    pj_path = os.path.join(exp, 'parts.json')
    if not os.path.exists(pj_path):
        out.update(ok=False, problems=['no parts.json']); res['export'] = out
        return False
    pj = json.load(open(pj_path))
    glb = os.path.join(exp, pj['glb'])
    if not os.path.exists(glb):
        out.update(ok=False, problems=['no ' + pj['glb']]); res['export'] = out
        return False
    summ = BK.glb_summary(glb)
    out['glb'] = {'bytes': os.path.getsize(glb), 'nodes': summ['nodes'], 'meshes': summ['meshes'], 'materials': summ['materials'],
                  'images': summ['images'], 'animations': summ['animations']}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    # the importer leaves the first clip playing: drop every action so the nodes stand at their rest pose
    for o in bpy.data.objects:
        if o.animation_data:
            o.animation_data.action = None
            for tr in list(o.animation_data.nla_tracks):
                o.animation_data.nla_tracks.remove(tr)
        if o.type == 'ARMATURE':
            for pb in o.pose.bones:
                pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
        else:
            pass
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    objs = {o.name: o for o in bpy.data.objects}
    nt = 0
    dev = 0.0
    for p in pj['parts']:
        o = objs.get(p['node'])
        if o is None or o.type != 'MESH':
            out['problems'].append('node %s missing or not a mesh' % p['node']); continue
        t = sum(len(q.vertices) - 2 for q in o.data.polygons)
        nt += t
        if t != p['tris']:
            out['problems'].append('%s: %d triangles in the GLB, %d in parts.json' % (p['node'], t, p['tris']))
        s = src['bounds'].get(p['id'])
        if s:
            co = np.array([tuple(o.matrix_world @ v.co) for v in o.data.vertices])
            e = float(max(np.abs(co.min(0) - np.array(s[0])).max(), np.abs(co.max(0) - np.array(s[1])).max()))
            dev = max(dev, e)
            if e > 0.00005:
                out['problems'].append('%s: bounds differ from the source by %.3f mm' % (p['node'], e * 1000))
        if p.get('parent') and p['parent'].startswith(family + '.'):
            want = p['parent'].replace('.', '_')
            q = o.parent; found = False
            while q is not None:
                if q.name == want:
                    found = True; break
                q = q.parent
            if not found:
                out['problems'].append('%s is not under %s' % (p['node'], want))
        names = [p['seat'].get('clear'), p.get('grab'), (p.get('tool') or {}).get('tip')]
        names += [n for pp in p.get('paths', []) for n in pp['nodes']] + [m['node'] for m in p.get('marks', [])] + [z['node'] for z in p.get('zones', [])]
        for n in names:
            if n and n not in objs:
                out['problems'].append('helper %s missing' % n)
        if p['seat'].get('clear') and p['seat']['clear'] in objs and src['clear'].get(p['id']):
            e = (objs[p['seat']['clear']].matrix_world.translation - Vector(src['clear'][p['id']])).length
            if e > 0.00005:
                out['problems'].append('%s__clear is %.3f mm from the source' % (p['node'], e * 1000))
    out['tris_total'] = nt
    out['max_bounds_dev_mm'] = round(dev * 1000, 4)
    out['helpers_in_glb'] = len([n for n in objs if '__' in n])
    # clips
    arm = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
    out['rig_imported_as'] = 'armature' if arm else 'nodes'
    for pr in pj.get('params', []):
        if pr.get('continuous'):
            if pr['bone'] not in summ['node_names']:
                out['problems'].append('continuous joint %s has no node in the GLB' % pr['bone'])
            continue
        a = summ['animations'].get(pr['action'])
        if not a:
            out['problems'].append('clip %s missing' % pr['action']); continue
        if abs(a['seconds'] - 1.0) > 1e-3:
            out['problems'].append('clip %s is %.4f s long, not 1 s' % (pr['action'], a['seconds']))
        if a['nodes'] != [pr['bone']]:
            out['problems'].append('clip %s moves %s, expected only %s' % (pr['action'], a['nodes'], pr['bone']))
        # end pose against the driven rig
        act = next((x for x in bpy.data.actions if x.name.startswith(pr['action'])), None)
        tgt = arm or objs.get(pr['bone'])
        ends = src['ends'].get(pr['id'].split('.', 1)[1], {})
        if act and tgt and ends:
            try:
                if not tgt.animation_data:
                    tgt.animation_data_create()
                tgt.animation_data.action = act
                try:
                    if tgt.animation_data.action_slot is None and act.slots:
                        tgt.animation_data.action_slot = act.slots[0]
                except Exception:
                    pass
                bpy.context.scene.frame_set(int(round(bpy.context.scene.render.fps * 1.0)) + 1)
                bpy.context.view_layer.update()
                dg = bpy.context.evaluated_depsgraph_get()
                worst = 0.0
                for nm, pos in ends.items():
                    if nm in objs:
                        worst = max(worst, (objs[nm].evaluated_get(dg).matrix_world.translation - Vector(pos)).length)
                out.setdefault('clip_end_pose_error_mm', {})[pr['action']] = round(worst * 1000, 4)
                if worst > 0.0002:
                    out['problems'].append('clip %s ends %.3f mm from the driven rig' % (pr['action'], worst * 1000))
                tgt.animation_data.action = None
                if tgt.type == 'ARMATURE':      # a removed action leaves its last pose behind: the next clip must start clean
                    for pb in tgt.pose.bones:
                        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
                bpy.context.scene.frame_set(1)
                bpy.context.view_layer.update()
            except Exception as e:
                out.setdefault('unverified', []).append('end pose of %s (%s)' % (pr['action'], e))
        elif ends:
            out.setdefault('unverified', []).append('end pose of %s (no action or target after import)' % pr['action'])
    out['ok'] = not out['problems']
    res['export'] = out
    return out['ok']


# ---------------------------------------------------------------------- externals
def load_external(blend, ids=None, after_sequence=True):
    """Bring another family's parts in (its source .blend, metres), with their helper empties. ids: which parts
    (default: all of them; the ones its own sequence has taken off start absent, i.e. the family arrives in its
    stripped state, and this family's sequence may insert them again). Returns {id: object}."""
    with bpy.data.libraries.load(blend, link=False) as (src, dst):
        dst.objects = list(src.objects)
        dst.scenes = list(src.scenes)
    scn = next((s for s in dst.scenes if s and s.get('sh_family')), None)
    gone = set()
    if scn is not None and after_sequence and ids is None:
        gone = set(json.loads(scn.get('sh_absent', '[]')))
        D = {json.loads(o['sh'])['id']: json.loads(o['sh']) for o in dst.objects if o and 'sh' in o}
        for e in json.loads(scn.get('sh_sequence', '[]')):
            if e['op'] == 'remove':
                gone.add(e['part'])
                stack = [e['part']]
                while stack:
                    x = stack.pop()
                    for c, d in D.items():
                        if d.get('parent') == x and c not in gone:
                            gone.add(c); stack.append(c)
            else:
                gone.discard(e['part'])
    out = {}
    for o in dst.objects:
        if o is None:
            continue
        bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.update()
    for o in dst.objects:
        if o is None or o.type != 'MESH' or 'sh' not in o:
            continue
        fid = json.loads(o['sh'])['id']
        if ids is None or fid in ids:
            out[fid] = o
            if ids is None and fid in gone:
                EXT_GONE.add(fid)
    for s in dst.scenes:
        if s is not None:
            bpy.data.scenes.remove(s)
    return out


# ---------------------------------------------------------------------- main
def main(family_dir, externals=None, skip_export=False):
    t0 = time.time()
    family_dir = os.path.abspath(family_dir)
    family = os.path.basename(family_dir.rstrip('/'))
    exp = os.path.join(family_dir, 'export')
    blend = os.path.join(exp, family + '.blend')
    res = {'family': family, 'generated': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'blender': bpy.app.version_string,
           'shrink_mm': SHRINK * 1000, 'contact_mm': CONTACT * 1000}
    if not os.path.exists(blend):
        res['ok'] = False; res['error'] = 'no %s: run build.py first' % blend
        json.dump(res, open(os.path.join(exp, 'check.json'), 'w'), indent=1)
        print('CHECK FAILED', res['error']); sys.exit(1)
    bpy.ops.wm.open_mainfile(filepath=blend)
    sc = bpy.context.scene
    P = CT.parts(family)
    ext = {}
    # stand-ins: meshes in this .blend registered under another family's id (looked for before anything else is loaded)
    local = {fid: o for fid, o in CT.parts().items() if fid.split('.')[0] != family}
    if local:
        ext.update(local); EXT_GONE.update(local)
        res['stand_ins'] = sorted(local)
    for e in externals or []:
        path, ids = e[0], (e[1] if len(e) > 1 else None)
        path = os.path.abspath(os.path.join(family_dir, path))
        ename = os.path.basename(path.rstrip('/'))
        got = load_external(os.path.join(path, 'export', ename + '.blend'), ids)
        ext.update(got)
        if len(e) > 2 and e[2] == 'absent':
            EXT_GONE.update(got)
        res.setdefault('externals', {})[ename] = sorted(got)
    if local:           # a stand-in gives way to the real part when its family is loaded
        res['stand_ins'] = sorted(f for f in local if ext[f] is local[f])
        res['stand_ins_replaced_by_the_real_part'] = sorted(f for f in local if ext[f] is not local[f])
    G = {o.name: Geo(o) for o in list(P.values()) + list(ext.values())}
    stats_path = os.path.join(exp, 'stats.json')
    budget = json.load(open(stats_path)).get('budget') if os.path.exists(stats_path) else None
    bad = CT.validate(family, budget)
    res['contract'] = {'ok': not bad, 'problems': bad, 'parts': len(P), 'tris': sum(CT.tris(o) for o in P.values()), 'budget': budget}
    ok = not bad
    ok = check_params(P, G, res) and ok
    ok = check_sequence(P, G, res, ext) and ok
    ok = check_fasteners(P, G, res, ext) and ok
    src = {'bounds': {}, 'clear': {}, 'ends': res.pop('_ends', {})}
    for fid, o in P.items():
        a, b = G[o.name].aabb(world_matrix(o))
        src['bounds'][fid] = ([float(x) for x in a], [float(x) for x in b])
        ce = bpy.data.objects.get(o.name + '__clear')
        if ce:
            src['clear'][fid] = [float(x) for x in world_matrix(ce).translation]
    if not skip_export:
        ok = check_export(family_dir, family, src, res) and ok
    res['ok'] = bool(ok)
    res['seconds'] = round(time.time() - t0, 1)
    json.dump(res, open(os.path.join(exp, 'check.json'), 'w'), indent=1)
    brief = {k: (res[k].get('ok') if isinstance(res.get(k), dict) else None) for k in ('contract', 'params', 'sequence', 'fasteners', 'export')}
    print('CHECK', 'PASS' if ok else 'FAIL', json.dumps(brief), flush=True)
    if not ok:
        for k in ('contract', 'export'):
            for p in (res.get(k) or {}).get('problems', []):
                print('  ', k, p)
        for k, v in (res.get('params') or {}).get('params', {}).items():
            if v.get('ok') is False:
                print('   param', k, {x: v[x] for x in ('overlap_at_rest', 'steps_with_new_overlap', 'first_new_overlap', 'clamp_error_mm')})
        for e in (res.get('sequence') or {}).get('events', []):
            if not e['ok']:
                print('   sequence', e.get('step'), e['op'], e['part'], e.get('error'))
        for k, v in (res.get('fasteners') or {}).get('fasteners', {}).items():
            if not v['ok']:
                print('   fastener', k, v.get('error'), v['holes'])
        sys.exit(1)


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    main(argv[argv.index('--family') + 1], skip_export='--noexport' in argv)
