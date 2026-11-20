"""Hero base: build the game's player file from the Rodin mesh on its Meshy rig (headless Blender 5.2).
Usage: blender.sh build_hero.py -- [tris=80000] [diffuse=<png>] [noclips]

The Meshy SmartRig is kept as it is for the body (so Meshy library clips play with no rest-pose matching), and the file
is shaped to the contract the game's installers expect (art/hero_base_20261120/PROGRESS.md):
  * armature object `Armature`, mesh `char1`, one material `PlayerSkin`;
  * 54 joints: the 24 game bones plus 30 finger bones renamed `{index,middle,ring,pinky,thumb}_{01,02,03}_{l,r}`;
    finger tip bones, toe ends and the six face bones go (face weights fold into `Head`);
  * finger bones re-rolled so a positive rotation about local X closes the finger, as on the previous (MPFB) rig;
    the convention is copied from the current colonist.glb, hand frame to hand frame, and tested joint by joint;
  * the mesh decimated to `tris` with the head and hands protected;
  * legacy clips `idle` (library 252), `walk`, `run` from the clips Meshy made on this rig: in place, collarbones
    anchored to the idle pose, loops closed (PlayerLocomotionTests).
Writes build/hero.blend, build/out/colonist.glb, build/out/TS_FPArms.glb, build/build.json and check renders."""
import bpy, sys, json, math, bmesh
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
opt = dict(a.split('=', 1) for a in args if '=' in a)
ROOT = Path('/home/teknetik/code/ao2'); H = ROOT / 'art/hero_base_20261120'; RIG = H / 'rig'; OUT = H / 'build'
OLD = ROOT / 'unity/AthenHill/Assets/AthenHill/Art/Imported/Meshy/colonist.glb'
TRIS = int(opt.get('tris', 80000)); NOCLIPS = 'noclips' in args
TEX = H / 'build/tex'
DIFFUSE = Path(opt.get('diffuse', str(TEX / 'hero_base.png')))
NORMAL = Path(opt.get('normal', str(TEX / 'hero_normal.png'))); ROUGH = Path(opt.get('rough', str(TEX / 'hero_rough.png')))
(OUT / 'out').mkdir(parents=True, exist_ok=True); (OUT / 'renders').mkdir(exist_ok=True)
rec = {'tris_target': TRIS, 'diffuse': str(DIFFUSE)}
DIG = {'Thumb': 'thumb', 'Index': 'index', 'Middle': 'middle', 'Ring': 'ring', 'Pinky': 'pinky'}
GAME = ['Hips', 'Spine02', 'Spine01', 'Spine', 'neck', 'Head', 'head_end', 'headfront'] + \
       [s + b for s in ('Left', 'Right') for b in ('Shoulder', 'Arm', 'ForeArm', 'Hand', 'UpLeg', 'Leg', 'Foot', 'ToeBase')]


def log(*a): print('BUILD', *a, flush=True)


def imp(path, merge=False):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path), merge_vertices=merge, bone_heuristic='BLENDER')
    new = [o for o in bpy.data.objects if o not in before]
    arm = next(o for o in new if o.type == 'ARMATURE')
    meshes = [o for o in new if o.type == 'MESH']
    return arm, (max(meshes, key=lambda o: len(o.data.vertices)) if meshes else None), new


def tris(o): return sum(len(p.vertices) - 2 for p in o.data.polygons)
def head(arm, n): return arm.matrix_world @ arm.data.bones[n].head_local


bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.fps = 30; sc.frame_start = 0
rig, char, _ = imp(RIG / 'rigged.glb', merge=True)
rig.name = 'Armature'; rig.data.name = 'Armature'; char.name = 'char1'; char.data.name = 'char1'
assert max(abs(x - 1) for x in rig.scale) < 1e-5 and rig.location.length < 1e-6, (tuple(rig.scale), tuple(rig.location))
rec['source'] = {'tris': tris(char), 'verts': len(char.data.vertices), 'bones': len(rig.data.bones)}
log('source', rec['source'])

# ------------------------------------------------------------------ mesh: weld seams by position, decimate, smooth
bpy.ops.object.select_all(action='DESELECT'); char.select_set(True); bpy.context.view_layer.objects.active = char
try:
    bpy.ops.mesh.customdata_custom_splitnormals_clear()
except Exception as e:
    log('no custom normals to clear', e)
bm = bmesh.new(); bm.from_mesh(char.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5); bm.to_mesh(char.data); bm.free()
vg = char.vertex_groups.new(name='protect')
gname = {g.index: g.name for g in char.vertex_groups}
PROT = lambda n: n in ('Head', 'neck', 'head_end', 'headfront') or n.startswith('Bone_') or 'Hand' in n
for v in char.data.vertices:
    w = sum(g.weight for g in v.groups if PROT(gname[g.group]))
    if w > 0.05: vg.add([v.index], min(1.0, w), 'REPLACE')
m = char.modifiers.new('dec', 'DECIMATE'); m.ratio = TRIS / tris(char); m.use_collapse_triangulate = True
m.vertex_group = 'protect'; m.vertex_group_factor = 4.0; m.invert_vertex_group = True
bpy.ops.object.modifier_apply(modifier='dec')
char.vertex_groups.remove(char.vertex_groups['protect'])
for p in char.data.polygons: p.use_smooth = True
rec['mesh'] = {'tris': tris(char), 'verts': len(char.data.vertices)}
log('decimated', rec['mesh'])

# ------------------------------------------------------------------ wrists: the Hand joint belongs at the narrowest section
# The auto-rig put the left Hand joint 20 mm up the forearm (the wrist band is on that arm); the right one is within
# 3 mm. Where a joint is more than 8 mm short of the wrist it is moved there along the forearm axis and the hand weight
# of the skin it no longer carries goes to the forearm.
def fix_wrist(side):
    Pn = lambda n: np.array(rig.matrix_world @ rig.data.bones[n].head_local)
    e = Pn(side + 'ForeArm'); k = Pn(side + 'HandMiddle1'); w = Pn(side + 'Hand'); ax = k - e; L = float(np.linalg.norm(ax)); ax /= L
    gn = {g.index: g.name for g in char.vertex_groups}
    idx = [v.index for v in char.data.vertices if sum(g.weight for g in v.groups if gn[g.group] == side + 'ForeArm' or gn[g.group].startswith(side + 'Hand')) > .6]
    pts = np.array([char.matrix_world @ char.data.vertices[i].co for i in idx]) - e
    sa = pts @ ax; ra = np.linalg.norm(pts - np.outer(sa, ax), axis=1)
    bins = np.arange(0.0, L, .005)
    prof = np.array([np.percentile(ra[(sa >= b) & (sa < b + .005)], 90) if ((sa >= b) & (sa < b + .005)).sum() > 8 else np.nan for b in bins])
    lo = int(len(bins) * .55); wrist_s = float(bins[lo + int(np.nanargmin(prof[lo:]))]) + .0025; joint_s = float((w - e) @ ax)
    shift = wrist_s - joint_s; out = {'joint_mm': round(joint_s * 1000, 1), 'wrist_mm': round(wrist_s * 1000, 1), 'shift_mm': round(shift * 1000, 1), 'moved': False}
    if shift < .008: return out
    bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    b = rig.data.edit_bones[side + 'Hand']; d = rig.matrix_world.inverted().to_3x3() @ Vector((ax * shift).tolist()); b.head += d; b.tail += d
    bpy.ops.object.mode_set(mode='OBJECT')
    hg_ = char.vertex_groups[side + 'Hand']; fg_ = char.vertex_groups[side + 'ForeArm']; changed = 0
    for n_, i_ in enumerate(idx):
        hw = next((g.weight for g in char.data.vertices[i_].groups if g.group == hg_.index), 0.0)
        if hw <= 0: continue
        t = min(1.0, max(0.0, (float(sa[n_]) - (wrist_s - .015)) / .030)); t = t * t * (3 - 2 * t)
        if hw * t < hw - 1e-4:
            hg_.add([i_], hw * t, 'REPLACE'); fg_.add([i_], hw * (1 - t), 'ADD'); changed += 1
    out.update(moved=True, vertices_reweighted=changed); return out


rec['wrists'] = {side: fix_wrist(side) for side in ('Left', 'Right')}
log('wrists', rec['wrists'])

# ------------------------------------------------------------------ previous rig: the finger axis convention to copy
old, old_mesh, old_objs = imp(OLD)
for o in old_objs:
    if o.type == 'MESH': bpy.data.objects.remove(o, do_unlink=True)
if old.animation_data: old.animation_data.action = None
for pb in old.pose.bones: pb.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()


def hand_frame(arm, side, names):
    """Orthonormal hand frame (columns): along the hand, along the knuckle line (index to pinky), palm normal."""
    w = head(arm, side + 'Hand'); a = (head(arm, names('middle', 1, side)) - w).normalized()
    k = head(arm, names('index', 1, side)) - head(arm, names('pinky', 1, side)); k = (k - a * k.dot(a)).normalized()
    return Matrix((a, k, a.cross(k))).transposed()


old_name = lambda d, j, side: f'{d}_0{j}_{"l" if side == "Left" else "r"}'
new_name = lambda d, j, side: f'{side}Hand{d.capitalize()}{j}'
conv = {}
for side in ('Left', 'Right'):
    Fo = hand_frame(old, side, old_name)
    for d in DIG.values():
        for j in (1, 2, 3):
            b = old.data.bones[old_name(d, j, side)]
            x_world = (old.matrix_world.to_3x3() @ b.matrix_local.to_3x3()).col[0].normalized()
            conv[old_name(d, j, side)] = tuple(Fo.transposed() @ x_world)       # the curl axis in hand-frame coordinates

# ------------------------------------------------------------------ armature: fold, drop, rename, re-roll
names = [b.name for b in rig.data.bones]
tips = [n for n in names if n.startswith('mixamorig:') or n.endswith(('Hand_End', 'Toe_end'))]
face = [n for n in names if n.startswith('Bone_')]
rec['dropped'] = {'tips': tips, 'face': face}
# face bone weights -> Head
hg = char.vertex_groups['Head']
for n in face:
    g = char.vertex_groups.get(n)
    if not g: continue
    for v in char.data.vertices:
        for e in v.groups:
            if e.group == g.index and e.weight > 0: hg.add([v.index], e.weight, 'ADD')
    char.vertex_groups.remove(g)
for n in tips:
    g = char.vertex_groups.get(n)
    if g:
        assert not any(e.group == g.index and e.weight > 1e-3 for v in char.data.vertices for e in v.groups), n
        char.vertex_groups.remove(g)
frames = {side: hand_frame(rig, side, new_name) for side in ('Left', 'Right')}
tip_of = {}
for n in tips:
    p = rig.data.bones[n].parent
    if p: tip_of[p.name] = head(rig, n)
bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
eb = rig.data.edit_bones
for n in tips + face: eb.remove(eb[n])
rename = {}
for side in ('Left', 'Right'):
    for D, d in DIG.items():
        for j in (1, 2, 3):
            src = f'{side}Hand{D}{j}'; dst = old_name(d, j, side); b = eb[src]
            nxt = eb.get(f'{side}Hand{D}{j + 1}')
            target = nxt.head.copy() if nxt else Vector(rig.matrix_world.inverted() @ tip_of[src]) if src in tip_of else None
            if target is not None and (target - b.head).length > 1e-4:
                b.tail = target                                   # the joint points at the next joint (or the old tip)
            y = (b.tail - b.head).normalized()
            x = (frames[side] @ Vector(conv[dst])); x = (x - y * x.dot(y)).normalized()
            b.align_roll(x.cross(y))                              # Z = X x Y for a right-handed bone frame
            rename[src] = dst
for src, dst in rename.items(): eb[src].name = dst
bpy.ops.object.mode_set(mode='OBJECT')
for src, dst in rename.items():
    g = char.vertex_groups.get(src)
    if g: g.name = dst
missing = [n for n in [b.name for b in rig.data.bones] if n not in char.vertex_groups and not n.endswith(('head_end', 'headfront'))]
rec['bones'] = [b.name for b in rig.data.bones]; rec['bone_count'] = len(rig.data.bones)
assert rec['bone_count'] == 54, rec['bone_count']
assert all(n in rig.data.bones for n in GAME), [n for n in GAME if n not in rig.data.bones]
log('bones', rec['bone_count'], 'without a vertex group:', missing)


# ---- test the curl: +40 degrees about local X must move the next joint the same way (in hand-frame terms) as on the old rig
def curl_test(arm, frame, bone, child_pos_fn):
    pb = arm.pose.bones[bone]; pb.rotation_mode = 'XYZ'
    p0 = child_pos_fn(); pb.rotation_euler = (math.radians(40), 0, 0); bpy.context.view_layer.update()
    p1 = child_pos_fn(); pb.rotation_euler = (0, 0, 0); bpy.context.view_layer.update()
    return (frame.transposed() @ (p1 - p0)).normalized()


def tail_world(arm, n): return arm.matrix_world @ arm.pose.bones[n].tail


agree = {}
for side in ('Left', 'Right'):
    Fo = hand_frame(old, side, old_name); Fn = frames[side]
    for d in DIG.values():
        for j in (1, 2, 3):
            n = old_name(d, j, side)
            a = curl_test(old, Fo, n, lambda: tail_world(old, n)); b = curl_test(rig, Fn, n, lambda: tail_world(rig, n))
            agree[n] = round(float(a.dot(b)), 3)
rec['curl_agreement'] = agree
bad = {k: v for k, v in agree.items() if v < 0.6}
log('curl agreement min', min(agree.values()), 'below 0.6:', bad)
assert not bad, bad
for o in [old]: bpy.data.objects.remove(o, do_unlink=True)

# ------------------------------------------------------------------ material and textures
mat = char.data.materials[0]
for m_ in list(bpy.data.materials):          # the previous colonist's materials came in with its rig: free the name
    if m_ is not mat: m_.name = 'previous_' + m_.name
mat.name = 'PlayerSkin'; assert mat.name == 'PlayerSkin', mat.name
nt = mat.node_tree
bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
base = bsdf.inputs['Base Color'].links[0].from_node


def tex(path, non_color):
    im = bpy.data.images.load(str(path)); im.colorspace_settings.name = 'Non-Color' if non_color else 'sRGB'; return im


base_name = base.name
for n in nt.nodes:                           # compare by name: `is` on bpy node wrappers is not identity
    if n.type == 'TEX_IMAGE' and n.image and n.name != base_name:
        n.image = tex(NORMAL, True) if 'normal' in n.image.name.lower() else tex(ROUGH, True)
base.image = tex(DIFFUSE, False)
rec['texture_nodes'] = {n.name: n.image.name for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image}
for im in list(bpy.data.images):
    if im.users == 0: bpy.data.images.remove(im)
rec['images'] = {i.name: list(i.size) for i in bpy.data.images if i.size[0] > 0}
char.parent = rig
if not any(md.type == 'ARMATURE' for md in char.modifiers):
    md = char.modifiers.new('Armature', 'ARMATURE'); md.object = rig
for md in char.modifiers:
    if md.type == 'ARMATURE': md.object = rig
# hands: two passes of neighbour averaging of the skin weights over the hand vertices, so the webs between the fingers
# stretch instead of tearing when the fingers close
HANDG = {g.index for g in char.vertex_groups if g.name.endswith(('_l', '_r')) or g.name in ('LeftHand', 'RightHand')}
hand_v = [v.index for v in char.data.vertices if sum(g.weight for g in v.groups if g.group in HANDG) > 0.5]
hv = set(hand_v); nb = {i: set() for i in hand_v}
for e in char.data.edges:
    a, b = e.vertices
    if a in hv: nb[a].add(b)
    if b in hv: nb[b].add(a)
wt = {v.index: {g.group: g.weight for g in v.groups} for v in char.data.vertices if v.index in hv or any(v.index in nb[i] for i in ())}
for i in hand_v:
    for j_ in nb[i]:
        if j_ not in wt: wt[j_] = {g.group: g.weight for g in char.data.vertices[j_].groups}
for _ in range(2):
    new_w = {}
    for i in hand_v:
        acc_ = {}
        for j_ in nb[i]:
            for g_, w_ in wt[j_].items(): acc_[g_] = acc_.get(g_, 0) + w_ / len(nb[i])
        mix = {g_: .5 * wt[i].get(g_, 0) + .5 * acc_.get(g_, 0) for g_ in set(wt[i]) | set(acc_)}
        new_w[i] = mix
    wt.update(new_w)
for i in hand_v:
    for g in list(char.data.vertices[i].groups): char.vertex_groups[g.group].remove([i])
    for g_, w_ in wt[i].items():
        if w_ > 1e-4: char.vertex_groups[g_].add([i], w_, 'REPLACE')
rec['hand_vertices_smoothed'] = len(hand_v)
# at most four weights a vertex, normalised
gi = {g.index: g.name for g in char.vertex_groups}
for v in char.data.vertices:
    ws = sorted(((g.weight, g.group) for g in v.groups if g.weight > 1e-4), reverse=True)
    keep = ws[:4]; tot = sum(w for w, _ in keep)
    for g in list(v.groups): char.vertex_groups[g.group].remove([v.index])
    for w, g in keep: char.vertex_groups[g].add([v.index], w / tot, 'REPLACE')
co = np.array([char.matrix_world @ v.co for v in char.data.vertices])
rec['bounds'] = [co.min(0).round(4).tolist(), co.max(0).round(4).tolist()]; rec['height'] = round(float(co[:, 2].max() - co[:, 2].min()), 4)

# ------------------------------------------------------------------ clips: idle, walk, run from the clips made on this rig
BODY = [n for n in GAME]
order = [b.name for b in rig.data.bones]


def sample(path):
    src, smesh, new = imp(path)
    for o in new:
        if o.type == 'MESH': bpy.data.objects.remove(o, do_unlink=True)
    act = src.animation_data.action; f0, f1 = [int(round(x)) for x in act.frame_range]
    rows = []
    for f in range(f0, f1 + 1):
        sc.frame_set(f); bpy.context.view_layer.update()
        rows.append({n: (src.matrix_world @ src.pose.bones[n].matrix).copy() for n in BODY})
    bpy.data.objects.remove(src, do_unlink=True)
    return rows


def set_pose(row):
    for pb in rig.pose.bones: pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update(); rinv = rig.matrix_world.inverted()
    for n in order:
        if n not in row: continue
        rig.pose.bones[n].matrix = rinv @ row[n]; bpy.context.view_layer.update()


def local_rows(rows):
    """World-matrix rows -> local pose values on the rig (rotation per body bone, hips location)."""
    out = []
    for row in rows:
        set_pose(row)
        out.append({'q': {n: rig.pose.bones[n].rotation_quaternion.copy() for n in BODY}, 'hip': rig.pose.bones['Hips'].location.copy(),
                    'arm': {s: (rig.matrix_world @ rig.pose.bones[s + 'Arm'].matrix).to_quaternion() for s in ('Left', 'Right')}})
    return out


def floor_now():
    dg = bpy.context.evaluated_depsgraph_get(); ev = char.evaluated_get(dg); me = ev.to_mesh()
    z = min((char.matrix_world @ v.co).z for v in me.vertices); ev.to_mesh_clear(); return z


def write(name, data):
    act = bpy.data.actions.new(name); rig.animation_data_create(); rig.animation_data.action = act
    for f, row in enumerate(data):
        for pb in rig.pose.bones: pb.matrix_basis = Matrix.Identity(4)
        for n in BODY:
            pb = rig.pose.bones[n]; pb.rotation_quaternion = row['q'][n]; pb.keyframe_insert('rotation_quaternion', frame=f)
        h = rig.pose.bones['Hips']; h.location = row['hip']; h.keyframe_insert('location', frame=f)
    for layer in act.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for k in fc.keyframe_points: k.interpolation = 'LINEAR'
    tr = rig.animation_data.nla_tracks.new(); tr.name = name; tr.strips.new(name, 0, act); tr.mute = True
    rig.animation_data.action = None
    return act


def average(qs):
    ref = qs[0]; v = [0., 0., 0., 0.]
    for q in qs:
        s = 1 if q.dot(ref) >= 0 else -1
        for k in range(4): v[k] += q[k] * s
    return Quaternion(v).normalized()


if not NOCLIPS:
    for pb in rig.pose.bones: pb.rotation_mode = 'QUATERNION'
    rec['clips'] = {}
    idle = local_rows(sample(RIG / 'idle_252.glb'))
    set_pose({}); rest_floor = floor_now()
    # idle: its own motion; only the loop is closed over the last fifth
    def close_loop(data):
        n = len(data)
        for f, row in enumerate(data):
            t = f / (n - 1); b = max(0, (t - .8) / .2); b = b * b * (3 - 2 * b)
            for k in BODY: row['q'][k] = row['q'][k].slerp(data[0]['q'][k], b) if f else row['q'][k]
            row['hip'] = row['hip'].lerp(data[0]['hip'], b)
        last = data[-1]
        for k in BODY: last['q'][k] = data[0]['q'][k].copy()
        last['hip'] = data[0]['hip'].copy()
    seam = max(math.degrees(idle[0]['q'][k].rotation_difference(idle[-1]['q'][k]).angle) for k in BODY)
    close_loop(idle); write('idle', idle)
    rec['clips']['idle'] = {'frames': len(idle), 'source': 'idle_252.glb', 'seam_before_deg': round(seam, 2)}
    neutral = {s: idle[0]['q'][s + 'Shoulder'].copy() for s in ('Left', 'Right')}
    for name, fn, keep in (('walk', 'basic_walking.glb', .22), ('run', 'basic_running.glb', .38)):
        rows = sample(RIG / fn); data = local_rows(rows)
        hips = [r['Hips'].translation.copy() for r in rows]
        drift = hips[-1] - hips[0]; drift.z = 0
        rec['clips'][name] = {'frames': len(data), 'source': fn, 'root_drift_m': round(drift.length, 4)}
        mean = {s: average([d['q'][s + 'Shoulder'] for d in data]) for s in ('Left', 'Right')}
        n = len(data); rinv = rig.matrix_world.inverted()
        for f, d in enumerate(data):
            # in place: take the linear travel out, keep sway and bounce
            if drift.length > 0.02:
                row = dict(rows[f]); mh = row['Hips'].copy(); mh.translation = mh.translation - drift * (f / (n - 1)); row['Hips'] = mh
                set_pose(row); d['hip'] = rig.pose.bones['Hips'].location.copy()
            # collarbones: the idle attachment plus a share of the clip's own motion; the arms keep their world swing
            for pb in rig.pose.bones: pb.matrix_basis = Matrix.Identity(4)
            for k in BODY: rig.pose.bones[k].rotation_quaternion = d['q'][k]
            rig.pose.bones['Hips'].location = d['hip']
            bpy.context.view_layer.update()
            for s in ('Left', 'Right'):
                c = rig.pose.bones[s + 'Shoulder']; delta = mean[s].inverted() @ d['q'][s + 'Shoulder']
                c.rotation_quaternion = neutral[s] @ Quaternion().slerp(delta, keep); bpy.context.view_layer.update()
                a = rig.pose.bones[s + 'Arm']; hw = (rig.matrix_world @ a.matrix).translation
                a.matrix = rinv @ (Matrix.Translation(hw) @ d['arm'][s].to_matrix().to_4x4()); bpy.context.view_layer.update()
                d['q'][s + 'Shoulder'] = c.rotation_quaternion.copy(); d['q'][s + 'Arm'] = a.rotation_quaternion.copy()
        seam = max(math.degrees(data[0]['q'][k].rotation_difference(data[-1]['q'][k]).angle) for k in BODY)
        close_loop(data)
        # ground: the lowest sole over the clip sits on the rest floor (walk) / never below it (run)
        lows = []
        for d in data:
            for pb in rig.pose.bones: pb.matrix_basis = Matrix.Identity(4)
            for k in BODY: rig.pose.bones[k].rotation_quaternion = d['q'][k]
            rig.pose.bones['Hips'].location = d['hip']; bpy.context.view_layer.update(); lows.append(floor_now())
        shift = rest_floor - min(lows)
        hip_b = rig.data.bones['Hips']; up_local = (hip_b.matrix_local.to_3x3().inverted() @ rig.matrix_world.to_3x3().inverted() @ Vector((0, 0, 1)))
        for d in data: d['hip'] = d['hip'] + up_local * shift
        write(name, data)
        rec['clips'][name].update({'seam_before_deg': round(seam, 2), 'ground_shift_m': round(shift, 4), 'clavicle_share': keep})
        log('clip', name, rec['clips'][name])
    for pb in rig.pose.bones: pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()

# ------------------------------------------------------------------ save and export
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'hero.blend'))


def export(objs, path, anims, images='AUTO'):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    rig.select_set(True); bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(filepath=str(path), use_selection=True, export_format='GLB', export_skins=True,
                              export_animations=anims, export_animation_mode='NLA_TRACKS', export_morph=False, export_yup=True,
                              export_image_format=images, export_tangents=True)


export([char], OUT / 'out' / 'colonist.glb', not NOCLIPS)
rec['glb_bytes'] = (OUT / 'out' / 'colonist.glb').stat().st_size

# ------------------------------------------------------------------ first-person arms: the body's own arms and hands
ARM = {f'{s}{b}' for s in ('Left', 'Right') for b in ('Arm', 'ForeArm', 'Hand')} | set(rename.values())
gname = {g.index: g.name for g in char.vertex_groups}


def dom(v):
    if not v.groups: return None
    return gname[max(v.groups, key=lambda g: g.weight).group]


keep = {v.index for v in char.data.vertices if dom(v) in ARM}
fa = char.copy(); fa.data = char.data.copy(); fa.name = 'TS_FPArms'; fa.data.name = 'TS_FPArms'
bpy.context.collection.objects.link(fa)
bm = bmesh.new(); bm.from_mesh(fa.data); bm.faces.ensure_lookup_table()
kill = [f for f in bm.faces if not all(v.index in keep for v in f.verts)]
bmesh.ops.delete(bm, geom=kill, context='FACES'); bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
bm.to_mesh(fa.data); bm.free(); fa.data.update()
rec['fp_arms'] = {'tris': tris(fa), 'verts': len(fa.data.vertices)}
export([fa], OUT / 'out' / 'TS_FPArms.glb', False, 'NONE')   # the installer maps the arms onto the body's material by name
bpy.data.objects.remove(fa, do_unlink=True)
(OUT / 'build.json').write_text(json.dumps(rec, indent=1))
log('done', {k: rec[k] for k in ('mesh', 'bone_count', 'height', 'glb_bytes', 'fp_arms')})
