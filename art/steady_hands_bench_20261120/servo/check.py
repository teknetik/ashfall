# servo/check.py: the kit's machine checks for a family with TWO rigs (the clips on the body, the gimbal on its
# cradle), plus the blocked-order tests PARTS.md promises. The kit's check.main() assumes one rig per family, so this
# file calls the kit's own check functions once per rig and re-does the clip end-pose test per armature. The kit is
# not edited. Run: SH/blender.sh servo/check.py      -> export/check.json, exit 1 on failure
import sys, os, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'kit'))
import bpy
import numpy as np
from mathutils import Vector, Matrix
import check as K
import contract as CT
import rig as RG

FAMILY = 'servo'
EXP = os.path.join(HERE, 'export')
LEVEL = {'gimbal_pitch': 0.5, 'gimbal_roll': 0.5}


def sweep(P, G, part, riders, others, steps=40, to_clear=True):
    """Move `part` (and riders) from rest to its __clear pose; return {step: {other: overlaps}}."""
    o = P[part]
    Mr = K.world_matrix(o); Mc = K.world_matrix(bpy.data.objects[o.name + '__clear'])
    rest = {c: K.world_matrix(P[c]) for c in riders}
    trees = {x: G[P[x].name].bvh(K.world_matrix(P[x])) for x in others}
    hits = {}
    for s in range(steps + 1):
        M = K.lerp_pose(Mr, Mc, s / steps)
        for nm, Mm in [(o.name, M)] + [(P[c].name, M @ Mr.inverted() @ rest[c]) for c in riders]:
            mb = G[nm].bvh(Mm, shrunk=True)
            for x in others:
                n = len(trees[x].overlap(mb))
                if n:
                    hits.setdefault(s, {})[x] = hits.get(s, {}).get(x, 0) + n
    return hits


def main():
    t0 = time.time()
    blend = os.path.join(EXP, FAMILY + '.blend')
    res = {'family': FAMILY, 'generated': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'blender': bpy.app.version_string,
           'shrink_mm': K.SHRINK * 1000, 'contact_mm': K.CONTACT * 1000,
           'note': 'two rigs: kit check functions called once per rig (servo/check.py)'}
    bpy.ops.wm.open_mainfile(filepath=blend)
    sc = bpy.context.scene
    P = CT.parts(FAMILY)
    G = {o.name: K.Geo(o) for o in P.values()}
    rigs = json.loads(sc['sv_rigs'])
    arms = {n: bpy.data.objects[n] for n in rigs}
    gim = arms['servo_gimbal_rig']; clip = arms['servo_rig']
    stats_path = os.path.join(EXP, 'stats.json')
    budget = json.load(open(stats_path)).get('budget') if os.path.exists(stats_path) else None
    bad = CT.validate(FAMILY, budget)
    res['contract'] = {'ok': not bad, 'problems': bad, 'parts': len(P), 'tris': sum(CT.tris(o) for o in P.values()), 'budget': budget}
    ok = not bad
    # ---- parameters, one rig at a time
    params = {}; ends = {}; okp = True
    for name, joints in rigs.items():
        sc['sh_rig'] = name; sc['sh_joints'] = json.dumps(joints)
        r = {}
        K.check_params(P, G, r)
        # The kit's clamp test (since its 18:01 update) compares the pose at -0.5 with the REST pose, which is only
        # right for a parameter that rests at 0. Redo it here against the pose at 0 for every joint of this rig.
        arm_ = arms[name]
        for j in joints:
            if j['continuous']:
                continue
            base = {k['param']: float(k.get('rest', 0.0)) for k in joints if not k['continuous']}
            base.update(j.get('requires') or {})
            mv = [o for o in P.values() if o.parent is arm_ and o.parent_type == 'BONE']

            def pose(val):
                v = dict(base); v[j['param']] = val
                RG.set_params(arm_, v)
                return {o.name: K.world_matrix(o).translation.copy() for o in mv}
            p1, p16, p0, pm = pose(1.0), pose(1.6), pose(0.0), pose(-0.5)
            over = max([(p16[n] - p1[n]).length for n in p1] + [0.0]); under = max([(pm[n] - p0[n]).length for n in p0] + [0.0])
            e = r['params']['params'][j['param']]
            e['clamp_error_mm_kit'] = e.get('clamp_error_mm')
            e['clamp_error_mm'] = [round(over * 1000, 4), round(under * 1000, 4)]
            e['ok'] = bool(not e['steps_with_new_overlap'] and not e['overlap_at_rest'] and over < 1e-5 and under < 1e-5 and e['moving'])
            e['rest'] = float(j.get('rest', 0.0))
        okp = all(v.get('ok', True) is not False for v in r['params']['params'].values()) and okp
        params.update(r['params']['params']); ends.update(r.get('_ends', {}))
        RG.set_params(gim, LEVEL)
    res['params'] = {'ok': okp, 'params': params, 'rest': {'servo.gimbal_pitch': 0.5, 'servo.gimbal_roll': 0.5}}
    ok = okp and ok
    # ---- the path sweep, clips driven by the events, gimbal level
    sc['sh_rig'] = clip.name; sc['sh_joints'] = json.dumps(rigs[clip.name])
    RG.set_params(gim, LEVEL)
    ok = K.check_sequence(P, G, res, {}) and ok
    ok = K.check_fasteners(P, G, res, {}) and ok
    # ---- order tests: what must be blocked is blocked, what must pass passes
    RG.set_params(clip, {'clip_1': 0.0, 'clip_2': 0.0, 'clip_3': 0.0}); RG.set_params(gim, LEVEL)
    f = FAMILY + '.'
    gimbal_kids = [x for x in P if x.startswith(f + 'gimbal_') and x != f + 'gimbal_cradle'] + [f + 'lead_coil_a', f + 'lead_coil_b', f + 'lead_sense']
    tests = []

    def t(name, part, riders, others, want_blocked):
        h = sweep(P, G, f + part, riders, [f + x for x in others])
        blocked = bool(h)
        first = min(h) if h else None
        tests.append({'test': name, 'want': 'blocked' if want_blocked else 'free', 'got': 'blocked' if blocked else 'free',
                      'first_step': first, 'by': sorted(h[first]) if h else [], 'ok': blocked == want_blocked})
    t('lid lifts with the three clips closed', 'case_lid', [], ['clip_1', 'clip_2', 'clip_3'], True)
    for i in (1, 2, 3):
        v = {'clip_1': 1.0, 'clip_2': 1.0, 'clip_3': 1.0}; v['clip_%d' % i] = 0.0
        RG.set_params(clip, v)
        t('lid lifts with only clip %d closed' % i, 'case_lid', [], ['clip_%d' % i], True)
    RG.set_params(clip, {'clip_1': 0.0, 'clip_2': 0.0, 'clip_3': 0.0})
    t('lid lifts with a case screw still in', 'case_lid', [], ['screw_case_a'], True)
    t('board lifts with the plug still on its header', 'board', [f + 'trim_resistor'], ['lead_plug'], True)
    t('middle gear lifts with the top gear on', 'gear_mid', [], ['gear_top'], True)
    t('low gear lifts with the middle gear on', 'gear_low', [], ['gear_mid'], True)
    t('gimbal lifts with the middle gear on', 'gimbal_cradle', gimbal_kids, ['gear_mid'], True)
    t('gimbal lifts with a trunnion screw in', 'gimbal_cradle', gimbal_kids, ['screw_trunnion_a'], True)
    t('rotor lifts with the retaining ring in', 'gimbal_rotor', [], ['gimbal_retainer'], True)
    # the board must pass the plug once it is tilted off: put the plug at its clear pose
    plug = P[f + 'lead_plug']
    keep = plug.matrix_world.copy()
    plug.matrix_world = K.world_matrix(bpy.data.objects[plug.name + '__clear'])
    bpy.context.view_layer.update()
    t('board lifts past the plug tilted off its header', 'board', [f + 'trim_resistor'], ['lead_plug'], False)
    plug.matrix_world = keep
    bpy.context.view_layer.update()
    res['order_tests'] = {'ok': all(x['ok'] for x in tests), 'tests': tests}
    ok = res['order_tests']['ok'] and ok
    # ---- grip/INTERFACE.md section 1: the unit's outside, and the envelope of its moving parts, measured in D
    RG.set_params(gim, LEVEL)
    cr = P[f + 'gimbal_cradle']
    Di = K.world_matrix(cr).inverted()
    cv = [v.co * 1000 for v in cr.data.vertices]            # the cradle's own frame is D
    rr = lambda v: (v.x * v.x + v.y * v.y) ** 0.5
    it = {'flange_d': round(2 * max(rr(v) for v in cv if v.z > -1.9), 3), 'flange_z': [round(min(v.z for v in cv if rr(v) > 13.6 and abs(v.x) > 2.2), 3), round(max(v.z for v in cv), 3)],
          'body_d': round(2 * max(rr(v) for v in cv if v.z < -2.1 and abs(v.x) > 2.05), 3), 'body_bottom_z': round(min(v.z for v in cv), 3),
          'key_r_out': round(max(-v.y for v in cv if abs(v.x) <= 2.001 and v.z < -2.1), 3), 'key_width': round(2 * max(abs(v.x) for v in cv if -v.y > 13.4 and v.z < -2.1), 3)}
    want = {'flange_d': 30.0, 'body_d': 26.0, 'body_bottom_z': -20.0, 'key_r_out': 14.5, 'key_width': 4.0}
    env = {'r_max': 0.0, 'z_min': 1e9, 'z_max': -1e9}
    movers = [f + x for x in ('gimbal_ring', 'gimbal_race', 'gimbal_rotor', 'gimbal_retainer', 'gimbal_coil', 'gimbal_grit_1', 'gimbal_grit_2', 'gimbal_grit_3')]
    for pv in (0.0, 0.5, 1.0):
        for rv in (0.0, 0.5, 1.0):
            RG.set_params(gim, {'gimbal_pitch': pv, 'gimbal_roll': rv})
            for x in movers:
                for q in G[P[x].name].world(Di @ K.world_matrix(P[x])):
                    q = q * 1000
                    env['r_max'] = max(env['r_max'], rr(q)); env['z_min'] = min(env['z_min'], q.z); env['z_max'] = max(env['z_max'], q.z)
    RG.set_params(gim, LEVEL)
    env = {k: round(v, 3) for k, v in env.items()}
    okI = all(abs(it[k] - want[k]) < 0.02 for k in want) and abs(it['flange_z'][1]) < 0.02 and abs(it['flange_z'][0] + 2.0) < 0.02 \
        and env['r_max'] <= 11.0 and env['z_min'] >= -19.0 - 1e-6 and env['z_max'] <= -0.3
    res['interface'] = {'ok': bool(okI), 'unit_measured_mm': it, 'unit_wanted_mm': want, 'moving_envelope_mm_over_9_poses': env,
                        'moving_envelope_allowed_mm': {'r_max': 11.0, 'z': [-19.0, -0.3]},
                        'note': 'the coil tails and the lead ends in the notches are not moving parts and lie outside r 11 by design'}
    ok = okI and ok
    # ---- export
    src = {'bounds': {}, 'clear': {}, 'ends': {}}
    for fid, o in P.items():
        a, b = G[o.name].aabb(K.world_matrix(o))
        src['bounds'][fid] = ([float(x) for x in a], [float(x) for x in b])
        ce = bpy.data.objects.get(o.name + '__clear')
        if ce:
            src['clear'][fid] = [float(x) for x in K.world_matrix(ce).translation]
    ok = K.check_export(HERE, FAMILY, src, res) and ok          # leaves the re-imported GLB as the open scene
    pj = json.load(open(os.path.join(EXP, 'parts.json')))
    objs = {o.name: o for o in bpy.data.objects}
    ep = {}; probs = []
    for pr in pj.get('params', []):
        if pr.get('continuous'):
            continue
        act = next((x for x in bpy.data.actions if x.name.startswith(pr['action'])), None)
        arm = next((o for o in bpy.data.objects if o.type == 'ARMATURE' and pr['bone'] in o.pose.bones), None)
        want = ends.get(pr['id'].split('.', 1)[1], {})
        if not (act and arm and want):
            probs.append('end pose of %s not verified (action %s, armature %s)' % (pr['action'], bool(act), bool(arm))); continue
        for pb in arm.pose.bones:          # a clip sampled earlier must not leave its pose behind
            pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
        if not arm.animation_data:
            arm.animation_data_create()
        for tr in list(arm.animation_data.nla_tracks):
            tr.mute = True
        arm.animation_data.action = act
        try:
            if arm.animation_data.action_slot is None and act.slots:
                arm.animation_data.action_slot = act.slots[0]
        except Exception:
            pass
        bpy.context.scene.frame_set(int(round(bpy.context.scene.render.fps * 1.0)) + 1)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        worst = max([(objs[nm].evaluated_get(dg).matrix_world.translation - Vector(pos)).length for nm, pos in want.items() if nm in objs] + [0.0])
        ep[pr['action']] = round(worst * 1000, 4)
        if worst > 0.0002:
            probs.append('clip %s ends %.3f mm from the driven rig' % (pr['action'], worst * 1000))
        arm.animation_data.action = None
        bpy.context.scene.frame_set(1)
    res['export']['clip_end_pose_error_mm'] = ep
    res['export']['problems'] += probs
    res['export']['ok'] = not res['export']['problems']
    ok = res['export']['ok'] and ok
    res['ok'] = bool(ok)
    res['seconds'] = round(time.time() - t0, 1)
    json.dump(res, open(os.path.join(EXP, 'check.json'), 'w'), indent=1)
    brief = {k: res[k].get('ok') for k in ('contract', 'params', 'sequence', 'fasteners', 'order_tests', 'interface', 'export')}
    print('   interface', json.dumps(res['interface']))
    print('CHECK', 'PASS' if ok else 'FAIL', json.dumps(brief), flush=True)
    for k in ('contract', 'export'):
        for p in res[k].get('problems', []):
            print('  ', k, p)
    for k, v in res['params']['params'].items():
        if v.get('ok') is False:
            print('   param', k, {x: v.get(x) for x in ('overlap_at_rest', 'steps_with_new_overlap', 'first_new_overlap', 'clamp_error_mm', 'note')})
        elif 'min_clearance_mm' in v:
            print('   param', k, 'ok, min clearance mm', v['min_clearance_mm'])
    for e in res['sequence']['events']:
        print('   seq', e.get('step'), e['op'], e['part'], 'OK' if e['ok'] else 'FAIL ' + str(e.get('error')), e.get('skipped', ''),
              'clear_mm', e.get('min_clearance_on_path_mm'), 'unexpected', e.get('unexpected_contacts'))
    for k, v in res['fasteners']['fasteners'].items():
        print('   fastener', k, 'OK' if v['ok'] else 'FAIL', v.get('error'), v['holes'], 'head_gap', v.get('head_gap_mm'))
    for x in tests:
        print('   order', 'OK  ' if x['ok'] else 'FAIL', x['test'], '->', x['got'], x['by'])
    if not ok:
        sys.exit(1)


main()
