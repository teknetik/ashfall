"""Tutorial set: the colonist's flight suit (main_char_OK, Meshy rig) refitted onto the MPFB body.
1. Pose the Meshy skeleton so every bone lies on the MPFB bone of the same name; apply → suit in MPFB proportions.
2. Cut the colonist's own head (face, beard, hair) and hands out of the suit.
3. Push the suit clear of the MPFB body; delete the MPFB body faces the suit hides.
4. Skin the suit from the MPFB body (game rig weights).
Usage: blender_mpfb.sh jumpsuit_fit.py -- BODY_TAG OUT_TAG"""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
import bpy, bmesh, math
from mathutils import Vector, Matrix
from fitlib import *

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
BODY_TAG = args[0] if args else 'v2'; TAG = args[1] if len(args) > 1 else 'v1'
COLLAR_Z = float(args[2]) if len(args) > 2 else 0.55
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'mpfb' / f'body_{BODY_TAG}.blend'))
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
body = next(o for o in bpy.data.objects if o.type == 'MESH' and o.name == 'Human')

# ---- 1. import the colonist and pose its skeleton onto the MPFB bones
objs = import_glb(RIG)
for o in objs:
    if o.type == 'MESH' and o.name.startswith('Icosphere'): bpy.data.objects.remove(o)
marm = next(o for o in objs if o.type == 'ARMATURE' and o.name in bpy.data.objects)
suit = next(o for o in objs if o.type == 'MESH' and o.name in bpy.data.objects)
suit.name = 'Jumpsuit'; suit.data.name = 'Jumpsuit'

def wb(arm, name):
    b = arm.data.bones[name]; mw = arm.matrix_world
    return mw @ b.head_local, mw @ b.tail_local, (mw.to_3x3() @ b.matrix_local.to_3x3()).normalized()

bpy.context.view_layer.objects.active = marm
bpy.ops.object.mode_set(mode='POSE')
order = []
def walk(b):
    order.append(b.name)
    for c in b.children: walk(c)
for b in marm.data.bones:
    if b.parent is None: walk(b)
inv = marm.matrix_world.inverted()
CHILD = {'Hips': 'Spine02', 'Spine02': 'Spine01', 'Spine01': 'Spine', 'Spine': 'neck', 'neck': 'Head', 'Head': 'head_end',
         'LeftShoulder': 'LeftArm', 'LeftArm': 'LeftForeArm', 'LeftForeArm': 'LeftHand',
         'RightShoulder': 'RightArm', 'RightArm': 'RightForeArm', 'RightForeArm': 'RightHand',
         'LeftUpLeg': 'LeftLeg', 'LeftLeg': 'LeftFoot', 'LeftFoot': 'LeftToeBase',
         'RightUpLeg': 'RightLeg', 'RightLeg': 'RightFoot', 'RightFoot': 'RightToeBase'}
def joint(arm, name): return arm.matrix_world @ arm.data.bones[name].head_local
# target joint positions: MPFB joints, except the spine/neck chain keeps the colonist's spacing along the MPFB line
tj = {n: joint(rig, n) for n in order if n in rig.data.bones}
chain = ['Hips', 'Spine02', 'Spine01', 'Spine', 'neck']
m0, m1 = joint(marm, 'Hips'), joint(marm, 'neck'); t0, t1 = tj['Hips'], tj['neck']
for n in chain[1:-1]:
    f = (joint(marm, n) - m0).dot(m1 - m0) / (m1 - m0).length_squared
    tj[n] = t0 + (t1 - t0) * f
R_obj = marm.matrix_world.to_3x3().normalized()
report = []; align_of = {}
for name in order:
    if name not in rig.data.bones: report.append(f'{name}: no MPFB bone'); continue
    b = marm.data.bones[name]
    mrot = (R_obj @ b.matrix_local.to_3x3()).normalized()
    th = tj[name]
    if name in CHILD:
        d0 = joint(marm, CHILD[name]) - joint(marm, name); d1 = tj[CHILD[name]] - th
        align = d0.normalized().rotation_difference(d1.normalized()).to_matrix(); ratio = d1.length / max(d0.length, 1e-6)
        ang = math.degrees(d0.angle(d1))
        if name in ('neck', 'Head'): ratio = 1.0   # keep the collar height; the MPFB neck is longer
        if name in ('LeftFoot', 'RightFoot'):   # boots stay flat on the ground: translate only, keep the colonist's size
            align = Matrix.Identity(3); ratio = 1.0
    elif False: pass
    else:   # leaf: follow the parent's alignment rigidly
        align = align_of.get(b.parent.name, Matrix.Identity(3)) if b.parent else Matrix.Identity(3); ratio = 1.0; ang = 0
    align_of[name] = align
    rw = align @ mrot
    S = Matrix.Identity(3)
    if name in CHILD:
        ax = rw.inverted() @ d1.normalized()
        S = Matrix.Identity(3) + (ratio - 1) * Matrix([[x * y for y in ax] for x in ax])
    b.inherit_scale = 'NONE'
    marm.pose.bones[name].matrix = Matrix.Translation(inv @ th) @ (R_obj.inverted() @ rw @ S).to_4x4()
    bpy.context.view_layer.update()
    report.append(f'{name}: len ratio {ratio:.3f} angle {ang:.1f}')
bpy.ops.object.mode_set(mode='OBJECT')
print('POSE\n' + '\n'.join(report))
# apply the pose to the suit mesh, then drop the Meshy skeleton
bpy.context.view_layer.objects.active = suit
for m in list(suit.modifiers):
    if m.type == 'ARMATURE': bpy.ops.object.modifier_apply(modifier=m.name)
suit.parent = None; suit.matrix_world = suit.matrix_world.copy()
apply(suit)

# ---- 2. cut the colonist's head and hands out of the suit (dominant-bone test)
CUT = {'Head', 'head_end', 'headfront', 'LeftHand', 'RightHand'}
gname = {g.index: g.name for g in suit.vertex_groups}
def dom(v):
    best = max(v.groups, key=lambda g: g.weight, default=None)
    return gname[best.group] if best else None
bm = bmesh.new(); bm.from_mesh(suit.data); bm.verts.ensure_lookup_table()
dl = bm.verts.layers.deform.verify()
def dom_bm(v):
    d = v[dl]
    if not d: return None
    gi = max(d.keys(), key=lambda k: d[k]); return gname[gi]
# skin test from the colonist's own base colour: his bare forearms (rolled sleeves) and neck are part of the suit mesh
img = None
for slot in suit.material_slots:
    for n in slot.material.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image and 'olor' in (n.label + n.image.name + ''.join(l.to_node.name for o in n.outputs for l in o.links)):
            img = n.image
    if img is None:
        for n in slot.material.node_tree.nodes:
            if n.type == 'TEX_IMAGE' and n.image: img = n.image; break
W, H = img.size; px = list(img.pixels[:])
uvl = bm.loops.layers.uv.active
def skin_at(uv):
    x = min(W - 1, max(0, int(uv.x % 1 * W))); y = min(H - 1, max(0, int(uv.y % 1 * H))); i = (y * W + x) * 4
    r, g, b = px[i], px[i + 1], px[i + 2]
    return r > 0.28 and r > g * 1.18 and r > b * 1.35          # warm skin vs olive/grey fabric and dark leather
SKINZONE = {'LeftForeArm', 'RightForeArm', 'neck', 'LeftHand', 'RightHand'}
def is_skin(f):
    if sum(1 for v in f.verts if dom_bm(v) in SKINZONE) < 2: return False
    return sum(1 for l in f.loops if skin_at(l[uvl].uv)) >= 2
print('SKIN image', img.name, W, H)
kill = [f for f in bm.faces if sum(1 for v in f.verts if dom_bm(v) in CUT) >= 2 or is_skin(f)]
bmesh.ops.delete(bm, geom=kill, context='FACES')
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
bm.to_mesh(suit.data); bm.free(); suit.data.update()
print('CUT faces', len(kill))
lo, hi = bounds(suit); print('SUIT bounds', [round(x, 3) for x in lo], [round(x, 3) for x in hi])

# soles back on the ground
lo, hi = bounds(suit); suit.location.z -= lo.z; apply(suit)
# ---- 3. clear the body: push the suit out, then delete the body faces it hides (keep head, neck top, hands)
neckz = (rig.matrix_world @ rig.data.bones['neck'].head_local).z
print('SHRINK', shrink_fit(suit, body, gap=0.02, k=0.85, radius=0.06, z_max=neckz - 0.03))
# collar: lower and snug it (the colonist's collar was cut for his larger Meshy head)
zc = neckz - 0.035
hz = (rig.matrix_world @ rig.data.bones['Head'].head_local).z
for v in suit.data.vertices:
    if v.co.z > zc: v.co.z = zc + (v.co.z - zc) * COLLAR_Z
suit.data.update()
print('COLLAR', shrink_fit(suit, body, gap=0.012, k=0.9, radius=0.035, iters=2), 'neck z %.3f head z %.3f' % (neckz, hz))
print('PUSH', push_out_smooth(suit, body, offset=0.005, radius=0.08, iters=10))
print('PEN after', penetration(suit, body))
# ---- 4. skin from the full MPFB body BEFORE hiding any of it (game-rig weights replace the colonist's groups)
clear_groups(suit)
skin_transfer(suit, body, bones=[b.name for b in rig.data.bones])
bind(suit, rig)
print('HIDDEN body faces', hide_covered(body, suit, reach=0.08, keep_groups=("Head", "neck", "LeftHand", "RightHand")))
print('HIDDEN near/feet', hide_near(body, suit, near=0.025, drop_groups=('LeftFoot', 'RightFoot', 'LeftToeBase', 'RightToeBase'),
                                    keep_groups=("Head", "neck", "LeftHand", "RightHand", "LeftForeArm", "RightForeArm")))
bpy.data.objects.remove(marm)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'mpfb' / f'suit_{TAG}.blend'))
for o in bpy.data.objects:
    if o.type == 'MESH' and o not in (suit,) and not o.name.startswith('Human'): o.hide_render = True
render_views(str(OUT / 'mpfb' / f'suit_{TAG}_raw'), (0, 0, 0.9), 1.9, views=('front', 'side', 'back'), res=(450, 900))
hd = rig.matrix_world @ rig.data.bones['Head'].head_local
render_views(str(OUT / 'mpfb' / f'suit_{TAG}_bust'), (hd.x, hd.y, hd.z - 0.05), 0.55, views=('front', 'quarter', 'side'), res=(500, 500))
