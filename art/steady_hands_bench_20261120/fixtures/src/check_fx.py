# check_fx.py: the fixtures family's own copy of tools/src/check_mb.py (model-bench, 21 Nov 2026: the tools family moved
# to model-tools, so fixtures keeps its checks here and tools/** is not touched). Added for Milestone 3: rests of the
# materials, grip, pistol and servo parts at the new pose marks (tray, mould, work mat, holster, press, entry places);
# an overlap sweep of the rigs the kit does not make (press lever with its ram, cure lamp arm); the tang mould seated
# in the press while the lever closes the top die on it; custom and skinned clips in the GLB check.
# check_mb.py: the machine checks of ANYMACHINE.md section 3 for the tools and fixtures families. Built from the kit's
# check.py (its Geo, parameter sweep and GLB reader are used as they are); the kit's main() assumes one rig per family
# and no skin, so the order of work is laid out here again.
#   SH/blender.sh <family>/check.py          -> <family>/export/check.json, exit 1 on failure
# 1. contract     kit contract.validate.
# 2. params       every driven rig, one at a time: 50 steps, triangle overlaps of the moving parts against the fixed
#                 ones, clearance, clamping (kit check_params). For tools the fixed set is the tool's own parts (a tool
#                 is swept in the hand, not in its pocket); for fixtures it is everything on the bench.
# 3. custom       rigs the kit does not make (the skinned roll, the dropper's bulb): clips there, one second long,
#                 poses finite, nothing through the bench, the bundle the size PARTS.md says.
# 4. seats        every part with a '__clear' pose and a rigid seat is moved between rest and clear in 40 steps against
#                 what it seats in: no overlap on the way (the assembly path sweep, for bits, dropper, moulds).
# 5. vise         the jaw parameter against measured pad gap, and a block of each thing the vise must hold closed on:
#                 the pads touch it, nothing else does.
# 6. export       the GLB read back: nodes, triangles, bounds, helper empties, clips, their length, what each clip
#                 moves and where it ends (read from the GLB's own accessors).
import bpy, os, sys, json, math, time, struct
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..', '..', 'tools', 'src')]
import mbk
from mbk import CT, RG, BK, PROG
import check as KC


def desc(P, root_id):
    """Ids of a part and everything under it in the contract tree."""
    out = {root_id}
    grew = True
    while grew:
        grew = False
        for fid, o in P.items():
            d = json.loads(o['sh'])
            if d['parent'] in out and fid not in out:
                out.add(fid); grew = True
    return out


def check_params(family, P, G, res):
    sc = bpy.context.scene
    rigs = json.loads(sc.get('sh_rigs', '{}'))
    out = {'ok': True, 'params': {}, 'rigs': sorted(rigs)}
    ends = {}
    keep_absent = sc.get('sh_absent', '[]')
    for rig, joints in rigs.items():
        arm = bpy.data.objects.get(rig)
        sc['sh_rig'] = rig; sc['sh_joints'] = json.dumps(joints)
        scope = 'bench'
        if family == 'tools' and arm is not None and arm.parent is not None and 'sh' in arm.parent:
            own = desc(P, json.loads(arm.parent['sh'])['id'])
            sc['sh_absent'] = json.dumps([fid for fid in P if fid not in own])
            scope = 'own parts'
        r = {}
        ok = KC.check_params(P, G, r)
        sc['sh_absent'] = keep_absent
        for k, v in r['params']['params'].items():
            v['rig'] = rig; v['against'] = scope
            out['params'][k] = v
        ends.update(r.get('_ends', {}))
        out['ok'] = out['ok'] and ok
    res['params'] = out
    return out['ok'], ends


def check_custom(family, P, res):
    sc = bpy.context.scene
    out = {'ok': True, 'rigs': {}}
    for c in json.loads(sc.get('sh_custom', '[]')):
        arm = bpy.data.objects.get(c['rig'])
        r = {'clips': {}, 'problems': []}
        if arm is None or not arm.animation_data:
            r['problems'].append('rig or its clips missing'); out['rigs'][c['rig']] = r; out['ok'] = False
            continue
        skinned = [o for o in P.values() if any(m.type == 'ARMATURE' and m.object is arm for m in o.modifiers)]
        riding = [o for o in P.values() if o.parent is arm and o.parent_type == 'BONE']
        for clip in c['clips']:
            tr = arm.animation_data.nla_tracks.get(clip)
            if tr is None:
                r['problems'].append('clip %s missing' % clip); continue
            st = tr.strips[0]
            secs = (st.action_frame_end - st.action_frame_start) / sc.render.fps
            rows = []
            for i in range(0, 25):
                v = i / 24.0
                mbk.sample_clip(arm, clip, v)
                dg = bpy.context.evaluated_depsgraph_get()
                lo = np.full(3, 1e9); hi = np.full(3, -1e9); finite = True
                for o in skinned + riding:
                    oe = o.evaluated_get(dg); me = oe.to_mesh()
                    co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
                    mw = np.array(oe.matrix_world)
                    w = co @ mw[:3, :3].T + mw[:3, 3]
                    finite = finite and bool(np.isfinite(w).all())
                    lo = np.minimum(lo, w.min(0)); hi = np.maximum(hi, w.max(0))
                    oe.to_mesh_clear()
                rows.append({'v': round(v, 3), 'min': [round(float(x), 4) for x in lo], 'max': [round(float(x), 4) for x in hi], 'finite': finite})
            zmin = min(x['min'][2] for x in rows)
            r['clips'][clip] = {'seconds': round(secs, 4), 'steps': len(rows), 'lowest_z_mm': round(zmin * 1000, 2),
                                'size_at_0_mm': [round((a - b) * 1000, 1) for a, b in zip(rows[0]['max'], rows[0]['min'])],
                                'size_at_1_mm': [round((a - b) * 1000, 1) for a, b in zip(rows[-1]['max'], rows[-1]['min'])]}
            if abs(secs - 1.0) > 1e-3:
                r['problems'].append('%s is %.3f s long' % (clip, secs))
            if not all(x['finite'] for x in rows):
                r['problems'].append('%s: non-finite vertices' % clip)
            if zmin < -0.004:
                r['problems'].append('%s goes %.1f mm below the bench' % (clip, -zmin * 1000))
        unpose_custom()
        r['ok'] = not r['problems']
        out['rigs'][c['rig']] = r
        out['ok'] = out['ok'] and r['ok']
    if family == 'tools' and 'tools_roll_rig' in out['rigs']:
        u = out['rigs']['tools_roll_rig']['clips'].get('roll_unroll_param')
        if u:
            # as found: a bundle about 85 mm across and 300 long (PARTS.md); unrolled: 560 x 300 plus the open flap
            b = u['size_at_0_mm']
            if not (60 <= b[2] <= 110 and 60 <= b[0] <= 420):
                out['rigs']['tools_roll_rig']['problems'].append('rolled bundle is %s mm' % b); out['rigs']['tools_roll_rig']['ok'] = False; out['ok'] = False
    res['custom'] = out
    return out['ok']


def unpose_custom():
    """Muting a clip leaves its bones where it last put them: put every bone of every rig back at rest."""
    mbk.rest_all()
    for o in bpy.data.objects:
        if o.type == 'ARMATURE':
            for c in json.loads(bpy.context.scene.get('sh_custom', '[]')):
                if c['rig'] == o.name:
                    for pb in o.pose.bones:
                        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()


def check_custom_sweep(P, G, res):
    """The rigs the kit does not make, with rigid parts on their bones (press lever and ram, cure lamp arm): 41 steps of
    each clip, triangle overlaps of the riding parts against everything else of the family and against each other."""
    sc = bpy.context.scene
    absent = set(json.loads(sc.get('sh_absent', '[]')))
    out = {'ok': True, 'clips': {}}
    byname = {o.name: fid for fid, o in P.items()}
    for c in json.loads(sc.get('sh_custom', '[]')):
        arm = bpy.data.objects.get(c['rig'])
        riding = [o for o in P.values() if o.parent is arm and o.parent_type == 'BONE']
        if arm is None or not riding:
            continue
        mbk.rest_all()
        fixed = [o for fid, o in P.items() if o not in riding and fid not in absent]
        ftree = {o.name: G[o.name].bvh(KC.world_matrix(o)) for o in fixed}
        fbox = {o.name: G[o.name].aabb(KC.world_matrix(o)) for o in fixed}
        for clip in c['clips']:
            rest_pairs, bad, near = None, [], 1.0
            for i in range(41):
                v = i / 40.0
                mbk.sample_clip(arm, clip, v)
                hits = {}
                cur = {o.name: (KC.world_matrix(o)) for o in riding}
                for o in riding:
                    mb = G[o.name].bvh(cur[o.name], shrunk=True)
                    lo, hi = G[o.name].aabb(cur[o.name])
                    for n, t in ftree.items():
                        flo, fhi = fbox[n]
                        if np.any(lo > fhi + 0.004) or np.any(hi < flo - 0.004):
                            continue
                        k = len(t.overlap(mb))
                        if k:
                            hits['%s x %s' % (byname[o.name], byname[n])] = k
                    for q in riding:
                        if q.name <= o.name or q.parent_bone == o.parent_bone:
                            continue
                        k = len(G[q.name].bvh(cur[q.name]).overlap(mb))
                        if k:
                            hits['%s x %s' % (byname[o.name], byname[q.name])] = k
                if i == 0:
                    rest_pairs = dict(hits)
                if hits:
                    bad.append({'v': round(v, 3), 'overlaps': hits})
            unpose_custom()
            r = {'ok': not bad, 'steps': 41, 'riding': sorted(byname[o.name] for o in riding), 'overlap_at_0': rest_pairs, 'bad_steps': bad[:6]}
            out['clips'][clip] = r
            out['ok'] = out['ok'] and r['ok']
    res['custom_sweep'] = out
    return out['ok']


def check_press_mould(P, G, res):
    """The tang mould (with its charge) seated on the press bed at seat_mould while the lever closes the top die on it."""
    tang, charge = P.get('fixtures.mould_tang'), P.get('fixtures.mould_charge')
    mark = bpy.data.objects.get('fixtures_press__mark_seat_mould')
    arm = bpy.data.objects.get('fixtures_press_lever_rig')
    if tang is None or mark is None or arm is None:
        res['press_mould'] = {'ok': True, 'note': 'press or mould not in this build'}
        return True
    mbk.rest_all()
    A = KC.world_matrix(tang); B = KC.world_matrix(mark)
    movers = [o for o in (tang, charge) if o is not None]
    place = {o.name: B @ A.inverted() @ KC.world_matrix(o) for o in movers}
    press = [o for fid, o in P.items() if fid.startswith('fixtures.press')]
    byname = {o.name: fid for fid, o in P.items()}
    out = {'ok': True, 'steps': []}
    gap_closed = None
    for i in range(21):
        v = i / 20.0
        mbk.sample_clip(arm, 'press_lever_param', v)
        hits = {}; near = 1.0
        for m in movers:
            mb = G[m.name].bvh(place[m.name], shrunk=True)
            for q in press:
                t = G[q.name].bvh(KC.world_matrix(q))
                k = len(t.overlap(mb))
                if k:
                    hits['%s x %s' % (byname[m.name], byname[q.name])] = k
                if m is tang and q.name == 'fixtures_press_ram':
                    for pt in G[m.name].samples(place[m.name])[::2]:
                        nn = t.find_nearest(pt, 0.01)
                        if nn[0] is not None:
                            near = min(near, nn[3])
        out['steps'].append({'v': v, 'overlaps': hits, 'die_gap_mm': round(near * 1000, 3) if near < 1 else None})
        if hits:
            out['ok'] = False
        if i == 20:
            gap_closed = near
    unpose_custom()
    # on the bed: the mould must sit on it (its underside within 0.5 mm of the bed's top)
    t = G[P['fixtures.press'].name].bvh(KC.world_matrix(P['fixtures.press']))
    nb = min((t.find_nearest(pt, 0.01)[3] or 1.0) if t.find_nearest(pt, 0.01)[0] is not None else 1.0 for pt in G[tang.name].samples(place[tang.name])[::2])
    out['on_bed_mm'] = round(nb * 1000, 3)
    out['closed_gap_mm'] = round(gap_closed * 1000, 3) if gap_closed and gap_closed < 1 else None
    if nb > 0.0005 or not gap_closed or gap_closed > 0.0006:
        out['ok'] = False
        out['error'] = 'the mould does not sit on the bed or the top die does not close on it'
    out['steps'] = [s_ for s_ in out['steps'] if s_['overlaps']][:5] or out['steps'][-1:]
    res['press_mould'] = out
    return out['ok']


def check_seats(family, P, G, res):
    """Rest <-> clear sweep for rigid seats. Cloth is not an obstacle (a pocket gives)."""
    out = {'ok': True, 'seats': {}}
    skip_obst = {fid for fid, o in P.items() if any(m.type == 'ARMATURE' for m in o.modifiers)}
    for fid, o in P.items():
        ce = bpy.data.objects.get(o.name + '__clear')
        d = json.loads(o['sh'])
        if ce is None or not d['parent'] or d['parent'] not in P:
            continue
        if d['parent'] in skip_obst:
            out['seats'][fid] = {'ok': True, 'note': 'seats in cloth (%s): not swept' % d['parent']}
            continue
        moving = [P[k] for k in desc(P, fid)]
        obst = [P[k] for k in desc(P, d['parent']) if P[k] not in moving]
        A = KC.world_matrix(o); B = KC.world_matrix(ce)
        rel = {m.name: A.inverted() @ KC.world_matrix(m) for m in moving}
        ob = {q.name: G[q.name].bvh(KC.world_matrix(q)) for q in obst}
        bad, clear_min, contacts = [], 1.0, set()
        for i in range(KC.STEPS_SEQ + 1):
            t = i / KC.STEPS_SEQ
            Mt = KC.lerp_pose(A, B, t)
            for m in moving:
                Mm = Mt @ rel[m.name]
                mb = G[m.name].bvh(Mm, shrunk=True)
                sm = G[m.name].samples(Mm)
                for q in obst:
                    n = len(ob[q.name].overlap(mb))
                    if n:
                        bad.append({'t': round(t, 3), 'pair': '%s x %s' % (m.name, q.name), 'tris': n})
                    for p in sm[::3]:
                        nn = ob[q.name].find_nearest(p, 0.003)
                        if nn[0] is not None:
                            clear_min = min(clear_min, nn[3])
                            if i == 0 and nn[3] < KC.CONTACT:
                                contacts.add(q.name)
        out['seats'][fid] = {'ok': not bad, 'against': [q.name for q in obst], 'steps': KC.STEPS_SEQ + 1, 'overlaps': bad[:6],
                             'min_clearance_mm': round(clear_min * 1000, 3) if clear_min < 1 else None, 'contact_when_seated': sorted(contacts),
                             'travel_mm': round((B.translation - A.translation).length * 1000, 1)}
        out['ok'] = out['ok'] and not bad
    res['seats'] = out
    return out['ok']


# what the vise must hold whose family has not exported yet: name, thickness between the jaws (mm), width along the
# jaws, depth below the jaw tops. PLACEHOLDER sizes; the pistol frame and the servo are checked with their real
# geometry in check_rests.
VISE_HOLDS = [('two stacked alloy sheets', 4.0, 110.0, 20.0, 'thickness from grip/INTERFACE.md (2 x 2.0); a block, not the materials export'),
              ('strap blank', 2.0, 90.0, 17.0, 'section from grip/INTERFACE.md (17 x 2); a block 90 long between the jaws, not the materials export'),
              ('grip core with gimbal cradle (press fit)', 58.0, 40.0, 30.0, 'placeholder')]


def jaw_frame(body):
    """The vise's jaw-line frame (origin on the mat under the jaw line), from its jaw_top mark: the body node's own
    origin is on the swivel axis since 21 Nov."""
    jt = bpy.data.objects.get(body.name + '__mark_jaw_top')
    M = KC.world_matrix(body)
    if jt is None:
        return M
    z = (M.to_3x3() @ Vector((0, 0, 1))).normalized()
    F_ = M.copy(); F_.translation = KC.world_matrix(jt).translation - z * 0.135
    return F_


def vise_open():
    sc = bpy.context.scene
    for p in json.loads(sc.get('sh_params', '[]')):
        if p['id'] == 'fixtures.vise_jaw':
            return abs(p['max'] - p['min']) / 1000.0
    return 0.09


def check_vise(P, G, res):
    arm = bpy.data.objects.get('fixtures_vise_rig')
    out = {'ok': True, 'holds': [], 'gap': []}
    if arm is None:
        res['vise'] = {'ok': True, 'note': 'no vise in this build'}
        return True
    OPEN = vise_open()
    out['opening_mm'] = round(OPEN * 1000, 2)
    pf, pm = P['fixtures.vise_pad_f'], P['fixtures.vise_pad_m']
    body = P['fixtures.vise']
    parts = [o for fid, o in P.items() if fid.startswith('fixtures.vise')]
    Bj = jaw_frame(body)
    Bi = Bj.inverted()

    def gap():
        a = np.array([tuple(Bi @ p) for p in G[pf.name].world(KC.world_matrix(pf))])
        b = np.array([tuple(Bi @ p) for p in G[pm.name].world(KC.world_matrix(pm))])
        return float(a[:, 1].min() - b[:, 1].max()), float(b[:, 1].max()), float(a[:, 2].max())
    for v in (0.0, 0.25, 0.5, 0.75, 1.0):
        RG.set_params(arm, {'vise_jaw': v})
        g, ym, ztop = gap()
        want = OPEN * (1 - v)
        out['gap'].append({'jaw': v, 'gap_mm': round(g * 1000, 3), 'expected_mm': round(want * 1000, 3)})
        if abs(g - want) > 0.0004:
            out['ok'] = False
    for name, th, wd, dp, src in VISE_HOLDS:
        v = 1.0 - th / (OPEN * 1000.0)
        RG.set_params(arm, {'vise_jaw': v})
        g, ym, ztop = gap()
        # a block that just fills the gap, hanging dp below the pad tops
        lo = Vector((-wd / 2000.0, ym + 0.00002, ztop - dp / 1000.0)); hi = Vector((wd / 2000.0, ym + g - 0.00002, ztop + 0.02))
        vs = [Bj @ Vector((x, y, z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
        fs = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        tris = []
        for f in fs:
            tris += [(f[0], f[1], f[2]), (f[0], f[2], f[3])]
        blk = BVHTree.FromPolygons(vs, tris, all_triangles=True)
        hits = {}
        for o in parts:
            n = len(G[o.name].bvh(KC.world_matrix(o)).overlap(blk))
            if n:
                hits[o.name] = n
        ok = not hits and 0.0 <= v <= 1.0 and abs(g * 1000 - th) < 0.5
        out['holds'].append({'thing': name, 'thickness_mm': th, 'depth_mm': dp, 'jaw': round(v, 4), 'gap_mm': round(g * 1000, 3),
                             'overlaps': hits, 'ok': ok, 'size_source': src})
        out['ok'] = out['ok'] and ok
    RG.set_params(arm, {'vise_jaw': 0.0})
    out['throat_mm'] = 43.0
    out['note'] = 'placeholder sizes for what has not exported; a block deeper than the throat (43 mm) would sit on the screw'
    res['vise'] = out
    return out['ok']


# rests of other families' parts on the fixtures, at the full-pose seat marks (SEAM.md section 2): owner, mark, family,
# the part whose node takes the mark's transform, and which of that family's parts are on it at that moment
PISTOL_STRIPPED = ['pistol.frame', 'pistol.barrel', 'pistol.dust_cover', 'pistol.trigger', 'pistol.cell_bus', 'pistol.cell_latch', 'pistol.status_lamp']
RESTS = [('fixtures.workmat', 'seat_pistol', 'pistol', 'pistol.frame', 'not:pistol.card_a,pistol.card_b', None),
         ('fixtures.vise', 'seat_work', 'pistol', 'pistol.frame', 'not:pistol.card_a,pistol.card_b,pistol.cell', 'vise'),
         ('fixtures.cradle', 'seat_frame', 'pistol', 'pistol.frame', PISTOL_STRIPPED, None),
         ('fixtures.pad', 'seat_cell', 'pistol', 'pistol.cell', ['pistol.cell'], None),
         ('fixtures.board', 'seat_card_before', 'pistol', 'pistol.card_a', ['pistol.card_a'], None),
         ('fixtures.board', 'seat_card_after', 'pistol', 'pistol.card_b', ['pistol.card_b'], None),
         ('fixtures.vise', 'seat_servo', 'servo', 'servo.case_body', 'all', 'vise'),
         # Milestone 3 (21 Nov): the places that had no mark
         ('fixtures.tray', 'seat_servo', 'servo', 'servo.case_body', 'all', None),
         ('fixtures.tray', 'seat_alloy', 'materials', 'materials.sheet_a', 'tree', None),
         ('fixtures.tray', 'seat_vial', 'materials', 'materials.vial', 'tree', None),
         ('fixtures.mould_tang', 'seat_core', 'grip', 'grip.core', ['grip.core'], None, {'exclude': ['fixtures.mould_charge'], 'touch': 0.0012, 'max_depth': 0.0003}),
         ('fixtures.mould_tang', 'seat_charge', 'materials', 'materials.sheet_a', ['materials.sheet_a', 'materials.sheet_a_offcut_1', 'materials.sheet_a_offcut_2'], None,
          {'exclude': ['fixtures.mould_charge']}),
         ('fixtures.workmat', 'seat_sheet', 'materials', 'materials.sheet_a', ['materials.sheet_a', 'materials.sheet_a_offcut_1', 'materials.sheet_a_offcut_2'], None),
         ('fixtures.workmat', 'seat_plate_l', 'materials', 'materials.sheet_a_plate', ['materials.sheet_a_plate'], None),
         ('fixtures.workmat', 'seat_plate_r', 'materials', 'materials.sheet_b_plate', ['materials.sheet_b_plate'], None),
         ('fixtures.workmat', 'seat_strap', 'materials', 'materials.sheet_a_strap', ['materials.sheet_a_strap'], None),
         ('fixtures.workmat', 'seat_spare', 'materials', 'materials.sheet_b_strap', ['materials.sheet_b_strap'], None),
         ('fixtures.holster', 'seat_pistol', 'pistol', 'pistol.frame', 'not:pistol.card_a,pistol.card_b', None, {'touch': 0.008}),
         ('fixtures.press', 'seat_pour', 'materials', 'materials.vial', 'tree', None, {'air': True}),
         ('fixtures.worksurface', 'entry_pistol', 'pistol', 'pistol.frame', 'not:pistol.card_a,pistol.card_b', None, {'air': True, 'floor': 0.0}),
         ('fixtures.worksurface', 'entry_servo', 'servo', 'servo.case_body', 'all', None, {'air': True, 'floor': 0.0}),
         ('fixtures.worksurface', 'entry_sheet_a', 'materials', 'materials.sheet_a', 'tree', None, {'air': True, 'floor': 0.0}),
         ('fixtures.worksurface', 'entry_vial', 'materials', 'materials.vial', 'tree', None, {'air': True, 'floor': 0.0})]


def tree_ids(ext, root, fam):
    """A part of another family and everything under it that is there as found."""
    pj = json.load(open(os.path.join(PROG, fam, 'export', 'parts.json')))
    gone = set(pj.get('absent_at_start', []))
    par = {json.loads(o['sh'])['id']: json.loads(o['sh']).get('parent') for o in ext.values()}
    out = {root}; grew = True
    while grew:
        grew = False
        for k, v in par.items():
            if v in out and k not in out and k not in gone:
                out.add(k); grew = True
    return [i for i in ext if i in out]


def check_rests(P, G, res):
    out = {'ok': True, 'rests': []}
    fams = {}
    arm = bpy.data.objects.get('fixtures_vise_rig')
    OPEN = vise_open()
    own = {o.name: o for o in P.values()}
    for spec in RESTS:
        owner, mark, fam, root, which, mode = spec[:6]
        opts = spec[6] if len(spec) > 6 else {}
        row = {'owner': owner, 'mark': mark, 'part': root}
        me = bpy.data.objects.get('%s__mark_%s' % (owner.replace('.', '_'), mark))
        blend = os.path.join(PROG, fam, 'export', fam + '.blend')
        if me is None or owner not in P:
            continue
        if not os.path.exists(blend):
            row.update(ok=True, note='%s has not exported: not checked' % fam); out['rests'].append(row); continue
        if fam not in fams:
            ext = KC.load_external(blend, ids=None, after_sequence=False)
            fams[fam] = (ext, {fid: KC.Geo(o) for fid, o in ext.items()}, {fid: KC.world_matrix(o) for fid, o in ext.items()})
        ext, EG, EW = fams[fam]
        if root not in ext:
            row.update(ok=False, error='%s is not in %s' % (root, fam)); out['rests'].append(row); out['ok'] = False; continue
        if which == 'all':
            ids = list(ext)
        elif which == 'tree':
            ids = tree_ids(ext, root, fam)
        elif isinstance(which, str) and which.startswith('not:'):
            ids = [i for i in ext if i not in which[4:].split(',')]
        else:
            ids = [i for i in which if i in ext]
        Sw = KC.world_matrix(me)
        place = {i: Sw @ EW[root].inverted() @ EW[i] for i in ids}
        row['parts'] = len(ids)
        if mode == 'vise' and arm is not None:
            body = P['fixtures.vise']; Bi = jaw_frame(body).inverted()
            # how far the moving pad has to come: the thing's near side inside the pad's footprint
            ys, yf = [], []
            for i in ids:
                for q in EG[i].world(place[i]):
                    l = Bi @ q
                    if abs(l.x) <= 0.042 and 0.1095 <= l.z <= 0.1356:
                        ys.append(l.y)
            if not ys:
                row.update(ok=False, error='nothing of %s is between the pads' % root); out['rests'].append(row); out['ok'] = False; continue
            need = -0.00006 - min(ys)            # gap wanted between the pad faces
            v = 1.0 - need / OPEN
            row.update(jaw=round(v, 4), gap_mm=round(need * 1000, 2), fixed_side_gap_mm=round((0.00006 - max(ys)) * 1000, 3))
            RG.set_params(arm, {'vise_jaw': max(0.0, v - 0.0003 / OPEN)})      # 0.3 mm short of touching
            if not 0.0 <= v <= 1.0:
                row['error'] = 'does not fit: needs %.1f mm, the vise opens %.0f' % (need * 1000, OPEN * 1000)
        hits, near = {}, 1.0
        trees = {n: G[n].bvh(KC.world_matrix(o)) for n, o in own.items()}
        skip = {P[x].name for x in opts.get('exclude', []) if x in P}
        for i in ids:
            mb = EG[i].bvh(place[i], shrunk=True)
            lo, hi = EG[i].aabb(place[i])
            for n, o in own.items():
                if n in skip:
                    continue
                flo, fhi = G[n].aabb(KC.world_matrix(o))
                if np.any(lo > fhi + 0.004) or np.any(hi < flo - 0.004):
                    continue
                k = len(trees[n].overlap(mb))
                if k:
                    hits['%s x %s' % (i, n)] = k
                    # where: the overlapping triangles of the resting part, in the owner's own frame (mm)
                    pr_ = trees[n].overlap(mb)
                    Oi = KC.world_matrix(P[owner]).inverted()
                    vs_ = [Oi @ q for q in EG[i].world(place[i])]
                    row.setdefault('where_mm', {})['%s x %s' % (i, n)] = [len(pr_), [round(float(np.min([v[a] for v in vs_])) * 1000, 1) for a in range(3)],
                                                                         [round(float(np.max([v[a] for v in vs_])) * 1000, 1) for a in range(3)]]
                if n == P[owner].name or n.startswith(P[owner].name + '_'):
                    for q in EG[i].samples(place[i])[::2]:
                        nn = trees[n].find_nearest(q, 0.004)
                        if nn[0] is not None:
                            near = min(near, nn[3])
        zmin = min(float(EG[i].aabb(place[i])[0][2]) for i in ids)
        if hits:
            # how deep: vertices of the resting part inside the owner's solid (odd ray crossings), and their depth
            depth, n_in = 0.0, 0
            for n, o in own.items():
                if not any(k.endswith(' x ' + n) for k in hits):
                    continue
                t = trees[n]
                for i in ids:
                    for q in EG[i].world(place[i]):
                        cnt, org = 0, q.copy()
                        for _ in range(64):
                            loc, nrm, idx, dist = t.ray_cast(org, Vector((0.0, 0.0, 1.0)))
                            if loc is None:
                                break
                            cnt += 1
                            org = loc + Vector((0.0, 0.0, 1e-6))
                        if cnt % 2 == 1:
                            n_in += 1
                            nn = t.find_nearest(q)
                            depth = max(depth, nn[3])
            row['penetration'] = {'vertices_inside': n_in, 'max_depth_mm': round(depth * 1000, 3)}
            if 'max_depth' in opts and depth <= opts['max_depth']:
                row['tolerated'] = 'triangle contact %d pairs, deepest vertex %.3f mm <= %.2f mm allowed' % (sum(hits.values()), depth * 1000, opts['max_depth'] * 1000)
                hits = {}
        row.update(overlaps=hits, nearest_to_owner_mm=round(near * 1000, 3) if near < 1 else None, lowest_z_mm=round(zmin * 1000, 2))
        touch = opts.get('touch', 0.0025)
        row['ok'] = not hits and 'error' not in row and (near < touch or opts.get('air'))
        if near >= touch and not opts.get('air'):
            row['error'] = row.get('error') or 'does not touch its owner (nearest %.2f mm)' % (near * 1000 if near < 1 else 99)
        if 'floor' in opts and zmin < opts['floor'] - 0.0005:
            row['ok'] = False; row['error'] = row.get('error') or 'goes %.1f mm through the worktop' % ((opts['floor'] - zmin) * 1000)
        out['rests'].append(row)
        out['ok'] = out['ok'] and row['ok']
        if mode == 'vise' and arm is not None:
            RG.set_params(arm, {'vise_jaw': 0.0})
    res['rests'] = out
    return out['ok']


def glb_accessor(js, rest, idx):
    a = js['accessors'][idx]; bv = js['bufferViews'][a['bufferView']]
    n = {'SCALAR': 1, 'VEC3': 3, 'VEC4': 4}[a['type']]
    off = 8 + bv.get('byteOffset', 0) + a.get('byteOffset', 0)      # skip the BIN chunk header
    return np.frombuffer(rest, dtype=np.float32, count=a['count'] * n, offset=off).reshape(a['count'], n)


def check_export(family_dir, family, src, res):
    out = {'ok': True, 'problems': []}
    exp = os.path.join(family_dir, 'export')
    pj = json.load(open(os.path.join(exp, 'parts.json')))
    glb = os.path.join(exp, pj['glb'])
    js, rest = BK.read_glb(glb)
    summ = BK.glb_summary(glb)
    out['glb'] = {'bytes': os.path.getsize(glb), 'nodes': summ['nodes'], 'meshes': summ['meshes'], 'materials': summ['materials'], 'images': summ['images'],
                  'skins': len(js.get('skins', [])), 'animations': {k: {'channels': v['channels'], 'seconds': v['seconds']} for k, v in summ['animations'].items()}}
    names = summ['node_names']
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        out['problems'].append('duplicate node names: %s' % dup[:8])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    bpy.context.scene.frame_set(0)       # the importer leaves a clip applied: time 0 of every clip is parameter 0
    bpy.context.view_layer.update()
    objs = {o.name: o for o in bpy.data.objects}
    nt = 0; dev = 0.0
    dg = bpy.context.evaluated_depsgraph_get()
    jn = {n.get('name'): n for n in js['nodes']}
    scale_params = {q['bone'] for q in pj.get('params', []) if q.get('type') == 'scale'}
    for p in pj['parts']:
        o = objs.get(p['node'])
        if o is not None and o.type == 'EMPTY' and 'skin' in jn.get(p['node'], {}):
            # Blender's importer gives a skinned node that has children an empty and puts the mesh beside it; in the
            # GLB itself the node carries the mesh and the skin
            o = next((q for q in bpy.data.objects if q.type == 'MESH' and q.name.startswith(p['node'] + '.')), None)
            out.setdefault('skinned_nodes', []).append(p['node'])
        if o is None or o.type != 'MESH' or 'mesh' not in jn.get(p['node'], {}):
            out['problems'].append('node %s missing or not a mesh' % p['node']); continue
        t = sum(len(q.vertices) - 2 for q in o.data.polygons)
        nt += t
        if t != p['tris']:
            out['problems'].append('%s: %d triangles in the GLB, %d in parts.json' % (p['node'], t, p['tris']))
        s = src['bounds'].get(p['id'])
        if p.get('rides') in scale_params:
            # Blender's importer leaves a scale clip applied; the GLB's own bone node is checked for a rest scale of 1
            bn = jn.get(p['rides'], {})
            if any(abs(x - 1.0) > 1e-6 for x in bn.get('scale', [1, 1, 1])):
                out['problems'].append('%s: bone %s has a rest scale in the GLB' % (p['node'], p['rides']))
            out.setdefault('bounds_not_compared', []).append(p['node'])
        elif s and not any(m.type == 'ARMATURE' for m in o.modifiers):
            co = np.array([tuple(o.matrix_world @ v.co) for v in o.data.vertices])
            e = float(max(np.abs(co.min(0) - np.array(s[0])).max(), np.abs(co.max(0) - np.array(s[1])).max()))
            dev = max(dev, e)
            if e > 0.00005:
                out['problems'].append('%s: bounds differ from the source by %.3f mm' % (p['node'], e * 1000))
        hn = [p['seat'].get('clear'), p.get('grab'), (p.get('tool') or {}).get('tip')]
        hn += [n for pp in p.get('paths', []) for n in pp['nodes']] + [m['node'] for m in p.get('marks', [])] + [z['node'] for z in p.get('zones', [])]
        for n in hn:
            if n and n not in objs:
                out['problems'].append('helper %s missing' % n)
        if p['seat'].get('clear') in objs and src['clear'].get(p['id']):
            e = (objs[p['seat']['clear']].matrix_world.translation - Vector(src['clear'][p['id']])).length
            if e > 0.00005:
                out['problems'].append('%s__clear is %.3f mm from the source' % (p['node'], e * 1000))
    out['tris_total'] = nt
    out['max_bounds_dev_mm'] = round(dev * 1000, 4)
    out['helpers_in_glb'] = len([n for n in objs if '__' in n])
    # clips: length, what they move, where they end (from the GLB's accessors)
    nidx = {n.get('name'): i for i, n in enumerate(js['nodes'])}
    anim = {a.get('name'): a for a in js.get('animations', [])}
    ends = {}
    for pr in pj.get('params', []):
        if pr.get('continuous'):
            if pr['bone'] not in nidx:
                out['problems'].append('continuous joint %s has no node in the GLB' % pr['bone'])
            continue
        a = anim.get(pr['action'])
        if a is None:
            out['problems'].append('clip %s missing' % pr['action']); continue
        sm = summ['animations'][pr['action']]
        if abs(sm['seconds'] - 1.0) > 1e-3:
            out['problems'].append('clip %s is %.4f s long, not 1 s' % (pr['action'], sm['seconds']))
        if pr['type'] in ('hinge', 'slide', 'scale'):
            if sm['nodes'] != [pr['bone']]:
                out['problems'].append('clip %s moves %s, expected only %s' % (pr['action'], sm['nodes'], pr['bone']))
            node = js['nodes'][nidx[pr['bone']]]
            for ch in a['channels']:
                path = ch['target']['path']
                val = glb_accessor(js, rest, a['samplers'][ch['sampler']]['output'])
                first, last = val[0], val[-1]
                if pr['type'] == 'slide' and path == 'translation':
                    travel = float(np.linalg.norm(last - first)) * 1000
                    ends[pr['id']] = {'travel_mm': round(travel, 3), 'expected_mm': abs(pr['max'] - pr['min'])}
                    if abs(travel - abs(pr['max'] - pr['min'])) > 0.05:
                        out['problems'].append('clip %s travels %.3f mm, expected %.3f' % (pr['action'], travel, abs(pr['max'] - pr['min'])))
                if pr['type'] == 'hinge' and path == 'rotation':
                    d = abs(float(np.dot(first, last)))
                    ang = math.degrees(2 * math.acos(min(1.0, d)))
                    ends[pr['id']] = {'turn_deg': round(ang, 3), 'expected_deg': abs(pr['max'] - pr['min'])}
                    if abs(ang - abs(pr['max'] - pr['min'])) > 0.1:
                        out['problems'].append('clip %s turns %.3f deg, expected %.3f' % (pr['action'], ang, abs(pr['max'] - pr['min'])))
                if pr['type'] == 'scale' and path == 'scale':
                    ends[pr['id']] = {'scale_end': [round(float(x), 4) for x in last], 'expected': pr['max']}
            if pr['id'] not in ends:
                out['problems'].append('clip %s has no %s channel' % (pr['action'], pr['type']))
        else:      # skinned or custom: every channel must be on the param's own bones
            bl = pr.get('bones') or []
            if isinstance(bl, str):
                stray = [n for n in sm['nodes'] if not n.startswith(bl.rstrip('*'))]
            else:
                stray = [n for n in sm['nodes'] if n not in bl]
            if stray:
                out['problems'].append('clip %s moves %s' % (pr['action'], stray[:5]))
            ends[pr['id']] = {'channels': sm['channels'], 'nodes': len(sm['nodes'])}
    out['clip_ends'] = ends
    out['ok'] = not out['problems']
    res['export'] = out
    return out['ok']


def main(family_dir, skip_export=False):
    t0 = time.time()
    family_dir = os.path.abspath(family_dir)
    family = os.path.basename(family_dir.rstrip('/'))
    exp = os.path.join(family_dir, 'export')
    blend = os.path.join(exp, family + '.blend')
    res = {'family': family, 'generated': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'blender': bpy.app.version_string,
           'shrink_mm': KC.SHRINK * 1000, 'contact_mm': KC.CONTACT * 1000}
    bpy.ops.wm.open_mainfile(filepath=blend)
    sc = bpy.context.scene
    mbk.rest_all()                   # custom rigs at their bind pose (the roll unrolled, the bulb full)
    P = CT.parts(family)
    G = {o.name: KC.Geo(o) for o in P.values()}
    st = json.load(open(os.path.join(exp, 'stats.json')))
    bad = CT.validate(family, st.get('budget'))
    res['contract'] = {'ok': not bad, 'problems': bad, 'parts': len(P), 'tris': sum(CT.tris(o) for o in P.values()), 'budget': st.get('budget')}
    ok = not bad
    okp, _ = check_params(family, P, G, res); ok = okp and ok
    ok = check_custom(family, P, res) and ok
    ok = check_seats(family, P, G, res) and ok
    ok = check_custom_sweep(P, G, res) and ok
    ok = check_press_mould(P, G, res) and ok
    if family == 'fixtures':
        ok = check_vise(P, G, res) and ok
    res['fasteners'] = {'ok': True, 'note': 'no part of this family is a fastener the player removes (bolts, rivets and screws here are fixed)'}
    src = {'bounds': {}, 'clear': {}}
    unpose_custom()
    for fid, o in P.items():
        a, b = G[o.name].aabb(KC.world_matrix(o))
        src['bounds'][fid] = ([float(x) for x in a], [float(x) for x in b])
        ce = bpy.data.objects.get(o.name + '__clear')
        if ce:
            src['clear'][fid] = [float(x) for x in KC.world_matrix(ce).translation]
    res['nobake'] = bool(st.get('nobake'))
    if family == 'fixtures':
        ok = check_rests(P, G, res) and ok      # after the source bounds: it links other families' parts into the scene
    if not skip_export:
        ok = check_export(family_dir, family, src, res) and ok
    res['ok'] = bool(ok)
    res['seconds'] = round(time.time() - t0, 1)
    json.dump(res, open(os.path.join(exp, 'check.json'), 'w'), indent=1)
    brief = {k: (res[k].get('ok') if isinstance(res.get(k), dict) else None) for k in ('contract', 'params', 'custom', 'custom_sweep', 'press_mould', 'seats', 'vise', 'rests', 'export')}
    print('CHECK', 'PASS' if ok else 'FAIL', json.dumps(brief), flush=True)
    if not ok:
        for k in ('contract', 'export'):
            for p in (res.get(k) or {}).get('problems', []):
                print('  ', k, p)
        for k, v in (res.get('params') or {}).get('params', {}).items():
            if v.get('ok') is False:
                print('   param', k, {x: v.get(x) for x in ('overlap_at_rest', 'steps_with_new_overlap', 'first_new_overlap', 'clamp_error_mm', 'note')})
        for k, v in (res.get('custom') or {}).get('rigs', {}).items():
            for p in v.get('problems', []):
                print('   custom', k, p)
        for k, v in (res.get('seats') or {}).get('seats', {}).items():
            if not v.get('ok'):
                print('   seat', k, v.get('overlaps'))
        for k, v in (res.get('custom_sweep') or {}).get('clips', {}).items():
            if not v.get('ok'):
                print('   sweep', k, json.dumps(v.get('bad_steps')[:3])[:600])
        pm = res.get('press_mould') or {}
        if not pm.get('ok', True):
            print('   press_mould', json.dumps({k: pm.get(k) for k in ('error', 'on_bed_mm', 'closed_gap_mm', 'steps')})[:800])
        for h in (res.get('vise') or {}).get('holds', []):
            if not h['ok']:
                print('   vise', h)
        if not (res.get('vise') or {}).get('ok', True):
            for g in (res.get('vise') or {}).get('gap', []):
                print('   vise gap', g)
        for r in (res.get('rests') or {}).get('rests', []):
            if not r.get('ok'):
                print('   rest', {k: r.get(k) for k in ('owner', 'mark', 'jaw', 'gap_mm', 'fixed_side_gap_mm', 'overlaps', 'nearest_to_owner_mm', 'error')})
        sys.exit(1)
