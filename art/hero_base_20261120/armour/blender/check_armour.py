"""Hero armour: check the seven output GLBs against the new body (build/out/colonist.glb + build/hero.blend).
Per piece: joint names equal (in order) and max inverse-bind-matrix difference against colonist.glb, triangle count
against the shipped piece, influences per vertex, which bones carry weight (and whether that is the piece's scheme),
unweighted / un-normalised vertices, root node, animations, material and textures identical to the shipped file, and
penetration against the body in the rest pose (fitlib.penetration: vertices inside, deepest) plus gap percentiles.
Usage: blender.sh check_armour.py          -> armour/check.json (exit code 1 if any hard check fails)"""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/hero_base_20261120/armour/blender'); sys.path.insert(0, '/home/teknetik/code/ao2/art/hero_base_20261120/armour')
import bpy, json, hashlib, os, time
import hlib as H
from glbinfo import Glb

sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
FING = [f'{d}_0{k}_{s}' for d in ('thumb', 'index', 'middle', 'ring', 'pinky') for k in (1, 2, 3) for s in 'lr']
SCHEME = {'helmet': {'Head'}, 'vest': set(H.TORSO) | {'LeftArm'}, 'carrier': set(H.TORSO),
          'arms': {'LeftForeArm', 'RightForeArm'}, 'legs': {'LeftLeg', 'RightLeg'},
          'boots': {'LeftFoot', 'RightFoot', 'LeftToeBase', 'RightToeBase'},
          'gloves': {'LeftHand', 'RightHand', 'LeftForeArm', 'RightForeArm'} | set(FING)}
ref = Glb(str(H.HERO_GLB)); rnames, ribm = ref.skin()
out = {'body': {'colonist_glb': str(H.HERO_GLB), 'sha256': sha(H.HERO_GLB), 'mtime': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(H.HERO_GLB))),
                'hero_blend_mtime': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(H.HERO))), 'joints': len(rnames)},
       'pieces': {}}
arm, body = H.load_hero(); got = H.load_pieces(arm, list(H.FILES))
ok_all = True
for key, fn in H.FILES.items():
    path = H.OUTD / fn; g = Glb(str(path)); s = g.summary(); s.pop('material_json')
    names, ibm = g.skin()
    d = max(abs(a - b) for ma, mb in zip(ibm, ribm) for a, b in zip(ma, mb)) if len(ibm) == len(ribm) else float('inf')
    old = Glb(str(H.TS_OLD / fn)); so = old.summary()
    def img_bytes(G):
        r = []
        for im in G.j.get('images', []):
            v = G.j['bufferViews'][im['bufferView']]; r.append(hashlib.sha256(G.bin[v.get('byteOffset', 0):v.get('byteOffset', 0) + v['byteLength']]).hexdigest())
        return r
    pen = H.penetration(got[key], body); gap = H.gap_stats(got[key], body)
    extra = sorted(set(s['weighted_bones']) - SCHEME[key])
    c = {
        'file': str(path), 'sha256': sha(path), 'bytes': s['bytes'],
        'mtime': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(path))),
        'newer_than_hero_blend': os.path.getmtime(path) > os.path.getmtime(H.HERO),
        'joints': len(names), 'joint_names_equal': names == rnames, 'ibm_max_diff': d,
        'root_node': s['scene_roots'], 'animations': s['animations'], 'mesh_node': s['mesh_nodes'], 'mesh': s['meshes'],
        'triangles': s['triangles'], 'triangles_shipped': so['triangles'], 'vertices': s['vertices'],
        'max_influences': s['max_influences'], 'influence_hist': s['influence_hist'], 'unweighted': s['unweighted'],
        'not_normalised': s['not_normalised'], 'weighted_bones': s['weighted_bones'], 'bones_outside_scheme': extra,
        'material': s['materials'], 'material_equal_to_shipped': g.j['materials'] == old.j['materials'],
        'images': [(i['name'], i['mime'], i['w'], i['h'], i['bytes']) for i in s['images']],
        'images_byte_identical_to_shipped': img_bytes(g) == img_bytes(old),
        'rest_penetration': {'vertices_inside': pen[0], 'deepest_mm': round(pen[1] * 1000, 2)}, 'rest_gap': gap,
    }
    hard = [c['joint_names_equal'], d < 1e-4, c['root_node'] == ['Armature'], c['animations'] == 0, c['mesh_node'] == so['mesh_nodes'],
            c['triangles'] <= so['triangles'], c['max_influences'] <= 4, c['unweighted'] == 0, c['not_normalised'] == 0,
            c['material_equal_to_shipped'], c['images_byte_identical_to_shipped'], c['newer_than_hero_blend'], not extra]
    c['pass'] = all(hard); ok_all &= c['pass']
    out['pieces'][key] = c
    print('CHECK %-8s %s joints %d names=%s ibm %.1e tris %d/%d infl %d unweighted %d bones %s pen %d (%.1f mm) gap p05/p50 %.1f/%.1f mm' % (
        key, 'PASS' if c['pass'] else 'FAIL', c['joints'], c['joint_names_equal'], d, c['triangles'], so['triangles'], c['max_influences'],
        c['unweighted'], ','.join(sorted(s['weighted_bones'])) if len(s['weighted_bones']) < 9 else '%d bones' % len(s['weighted_bones']),
        pen[0], pen[1] * 1000, gap.get('p05_mm', 0), gap.get('p50_mm', 0)), 'OUTSIDE SCHEME ' + str(extra) if extra else '', flush=True)
# the torso pieces are fitted to the shoulders as the game holds them (hlib 'neutral': the idle clip's collarbones and
# arms on an upright spine), so that pose is measured too
H.set_pose(arm, body, 'neutral')
for key in H.FILES:
    out['pieces'][key]['neutral_pose_penetration'] = H.posed_penetration(got[key], body)
    print('CHECK %-8s neutral pose' % key, out['pieces'][key]['neutral_pose_penetration'], flush=True)
H.rest(arm)
out['pass'] = ok_all
out['notes'] = ['pass = the hard checks: joints/names/inverse bind matrices against colonist.glb, root node, no animations, mesh node name, '
                'triangles <= shipped, <= 4 normalised influences, no unweighted vertices, material and textures identical to the shipped '
                'file, bones within the piece scheme, file newer than hero.blend.',
                'rest_penetration is reported, not gated: vest and carrier are fitted in the neutral pose (see README), so they intersect '
                'the A-pose rest shoulders by design; the limb pieces, helmet and gloves are fitted in the rest pose.']
motion = H.WORK / 'motion.json'
if motion.exists(): out['motion_poke_through'] = {'note': 'piece vertices inside the deformed body per pose: inside / deeper than 3 mm / worst mm (blender/check_motion.py)',
                                                  'poses': json.loads(motion.read_text())}
(H.HERE / 'check.json').write_text(json.dumps(out, indent=1))
print('CHECK overall', 'PASS' if ok_all else 'FAIL')
sys.exit(0 if ok_all else 1)
