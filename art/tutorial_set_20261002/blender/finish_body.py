"""Tutorial set: finish the MPFB player body for Unity.
- Clean Principled materials (glTF-friendly): crash-repaired suit (Meshy retexture base/roughness/metallic + the colonist's
  4k baked fold normal), MPFB skin, eyes, alpha-clipped brows/lashes/hair/beard.
- One skinned mesh object 'char1' on the renamed game_engine rig 'Armature'.
- idle/walk/run retargeted from the colonist's Meshy clips (world-space bind-pose delta, hips height-scaled).
- Export art/tutorial_set_20261002/out/colonist_mpfb.glb + renders.
Usage: blender_mpfb.sh finish_body.py -- SUIT_TAG [drop=18] [face=old] [noanim]
3 Oct 2026 (art/player_face_20261003): the skin is the Meshy retexture of this MPFB skin mesh (painted face, hair, beard,
normal and roughness, original UVs) and the hair/beard/brow cards are replaced by alpha-clipped shell layers on the
painted hair. `face=old` rebuilds the previous MakeHuman skin + cards look."""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
import bpy, math, json
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
from fitlib import *

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
TAG = args[0] if args else 'v5'
NOANIM = 'noanim' in args
OLDFACE = 'face=old' in args
PF = AO2 / 'art/player_face_20261003'
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'mpfb' / f'suit_{TAG}.blend'))
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
rig.name = 'Armature'
JS = AO2 / 'meshy/tutorial-set-20261002/jumpsuit'
MC = AO2 / 'meshy/main-char-20261002'
TEX = OUT / 'tex'
EYES = Path('/home/teknetik/.config/blender/5.2/extensions/.user/user_default/mpfb/data/eyes/materials')
rec = {'suit': TAG}

def img(path, non_color=False):
    im = bpy.data.images.load(str(path), check_existing=True)
    if non_color: im.colorspace_settings.name = 'Non-Color'
    return im

def first_image(o):
    for s in o.material_slots:
        if s.material and s.material.use_nodes:
            for n in s.material.node_tree.nodes:
                if n.type == 'TEX_IMAGE' and n.image and 'normal' not in n.image.name.lower(): return n.image
    return None

def make_mat(name, base, rough=0.6, metal=0.0, normal=None, rough_img=None, metal_img=None, alpha=False, normal_strength=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; bs = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = base; nt.links.new(t.outputs['Color'], bs.inputs['Base Color'])
    if alpha:   # Round between alpha and the BSDF: Blender's glTF exporter writes alphaMode MASK (cutoff 0.5), not BLEND
        rnd = nt.nodes.new('ShaderNodeMath'); rnd.operation = 'ROUND'
        nt.links.new(t.outputs['Alpha'], rnd.inputs[0]); nt.links.new(rnd.outputs[0], bs.inputs['Alpha'])
        m.blend_method = 'CLIP' if hasattr(m, 'blend_method') else None
        try: m.surface_render_method = 'DITHERED'
        except Exception: pass
    bs.inputs['Roughness'].default_value = rough; bs.inputs['Metallic'].default_value = metal
    if rough_img or metal_img:
        # glTF wants roughness in G and metallic in B of one image: combine
        sep = nt.nodes.new('ShaderNodeSeparateColor')
        if rough_img:
            tr = nt.nodes.new('ShaderNodeTexImage'); tr.image = rough_img
            nt.links.new(tr.outputs['Color'], bs.inputs['Roughness'])
        if metal_img:
            tm = nt.nodes.new('ShaderNodeTexImage'); tm.image = metal_img
            nt.links.new(tm.outputs['Color'], bs.inputs['Metallic'])
    if normal:
        tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = normal
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = normal_strength
        nt.links.new(tn.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], bs.inputs['Normal'])
    if alpha:
        m['gltf_alpha_mode'] = 'MASK'
    return m

def set_mat(o, m):
    o.data.materials.clear(); o.data.materials.append(m)

# ---- materials
parts = {o.name: o for o in bpy.data.objects if o.type == 'MESH'}
print('PARTS', list(parts))
suit = parts['Jumpsuit']
set_mat(suit, make_mat('PlayerJumpsuit', img(TEX / 'suit_base.png'), normal=img(MC / 'blender/player_normal_4k.png', True),
                       rough_img=img(TEX / 'suit_roughness.png', True), metal_img=img(JS / 'tex0_metallic.png', True)))
for name, o in parts.items():
    if name == 'Jumpsuit': continue
    low = name.lower(); im = first_image(o)
    if low == 'human' and not OLDFACE:
        set_mat(o, make_mat('PlayerSkin', img(PF / 'tex/skin_base.png'), normal=img(PF / 'tex/skin_normal.png', True),
                            rough_img=img(PF / 'tex/skin_rough.png', True)))
        rec.setdefault('materials', {})[name] = 'PlayerSkin ' + str(PF / 'tex/skin_base.png'); continue
    elif low == 'human':
        set_mat(o, make_mat('PlayerSkin', im, rough=0.52))
    elif 'beard' in low:
        set_mat(o, make_mat('PlayerBeard', img(TEX / 'beard_rgba.png'), rough=0.7, alpha=True))
    elif 'high-poly' in low or 'eye' == low[-3:]:
        set_mat(o, make_mat('PlayerEyes', img(EYES / 'brown_eye.png') if OLDFACE else img(PF / 'tex/eye_brown.png'), rough=0.15))
    else:   # brows, lashes, hair
        set_mat(o, make_mat('Player' + name.split('.')[-1].capitalize(), im, rough=0.65, alpha=True))
    rec.setdefault('materials', {})[name] = o.data.materials[0].name + (' ' + im.filepath if im else '')

# ---- painted hair (3 Oct 2026): the card hair, beard and brows go; shells on the painted hair give the volume
if not OLDFACE:
    for name in list(parts):
        if any(k in name.lower() for k in ('short02', 'beard', 'eyebrow')):
            bpy.data.objects.remove(parts.pop(name)); rec.setdefault('cards_removed', []).append(name)
    sys.path.insert(0, str(PF / 'blender')); import shells
    sh, rec['hair_shells'] = shells.build_shells(parts['Human'], rig); parts['HairShells'] = sh
    print('SHELLS', rec['hair_shells'])
# every part carries the 'Col' colour attribute (white, alpha 1) so the joined mesh exports one COLOR_0 that glTF
# multiplies into base colour/alpha; only the shell layers have alpha < 1
for name, o in parts.items():
    ca = o.data.color_attributes.get('Col') or o.data.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    if name != 'HairShells':
        for d in ca.data: d.color = (1, 1, 1, 1)
    o.data.color_attributes.active_color = ca

# ---- eyes: drop the clear cornea shells (they map to the texture's corner disc and would render opaque over the iris)
import bmesh
for name, o in parts.items():
    if 'high-poly' not in name: continue
    bm = bmesh.new(); bm.from_mesh(o.data); uvl = bm.loops.layers.uv.active
    kill = [f for f in bm.faces if all(l[uvl].uv.x > 0.85 and l[uvl].uv.y < 0.15 for l in f.loops)]
    bmesh.ops.delete(bm, geom=kill, context='FACES'); bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(o.data); bm.free(); rec['cornea_faces_removed'] = len(kill)

# ---- rest pose matched to the Meshy rig: the clips are transferred as rotations relative to the rest pose (here and in
# CharacterFeelPass), so every bone segment must point where the colonist's did. MPFB's A-pose had the arms 19 deg
# higher, forearms 29 deg and feet 27 deg off, which put the weapon holds overhead. Parents first; twist kept.
MCHILD = {'Hips': 'Spine02', 'Spine02': 'Spine01', 'Spine01': 'Spine', 'Spine': 'neck', 'neck': 'Head', 'Head': 'head_end',
          'LeftShoulder': 'LeftArm', 'LeftArm': 'LeftForeArm', 'LeftForeArm': 'LeftHand',
          'RightShoulder': 'RightArm', 'RightArm': 'RightForeArm', 'RightForeArm': 'RightHand',
          'LeftUpLeg': 'LeftLeg', 'LeftLeg': 'LeftFoot', 'LeftFoot': 'LeftToeBase',
          'RightUpLeg': 'RightLeg', 'RightLeg': 'RightFoot', 'RightFoot': 'RightToeBase'}
_before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=str(MC / 'rigged.glb'))
_new = [o for o in bpy.data.objects if o not in _before]; _m = next(o for o in _new if o.type == 'ARMATURE')
mdir = {n: ((_m.matrix_world @ _m.data.bones[c].head_local) - (_m.matrix_world @ _m.data.bones[n].head_local)).normalized() for n, c in MCHILD.items()}
for o in _new: bpy.data.objects.remove(o)
bpy.context.view_layer.objects.active = rig
order = [b.name for b in rig.data.bones]
# 3 Oct 2026: limbs only. Matching the torso too copied the Meshy auto-rig's curved spine joint line onto the MPFB body
# (Hips 18, Spine 18-29 per segment, collarbones 10-11, head 26 deg), which baked a hunched back and shrugged shoulders
# into the rest pose and every clip. The torso keeps MPFB's own straight rest; the clip transfer is a world-space delta.
LIMBS = {f'{s}{b}' for s in ('Left', 'Right') for b in ('Arm', 'ForeArm', 'UpLeg', 'Leg', 'Foot')}
match = {}
# collarbones dropped first (the MPFB A-pose holds the shoulder girdle raised; lowering only the arms bunched the deltoid
# and trapezius skin up beside the neck). Rotate each clavicle's tail downward about its own head.
DROP = float(next((a.split('=')[1] for a in args if a.startswith('drop=')), '18'))
for n in ('LeftShoulder', 'RightShoulder'):
    pb = rig.pose.bones[n]
    h = rig.matrix_world @ pb.head; ch = rig.matrix_world @ rig.pose.bones[MCHILD[n]].head
    d = (ch - h).normalized(); axis = d.cross(Vector((0, 0, -1))).normalized()
    W = Matrix.Translation(h) @ Matrix.Rotation(math.radians(DROP), 4, axis) @ Matrix.Translation(-h)
    pb.matrix = rig.matrix_world.inverted() @ W @ rig.matrix_world @ pb.matrix
    bpy.context.view_layer.update()
rec['clavicle_drop_deg'] = DROP
for n in order:
    if n not in MCHILD or n not in LIMBS: continue
    pb = rig.pose.bones[n]
    h = (rig.matrix_world @ pb.head); ch = rig.matrix_world @ rig.pose.bones[MCHILD[n]].head
    d = (ch - h).normalized(); q = d.rotation_difference(mdir[n])
    match[n] = round(math.degrees(d.angle(mdir[n])), 1)
    W = Matrix.Translation(h) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h)
    pb.matrix = rig.matrix_world.inverted() @ W @ rig.matrix_world @ pb.matrix
    bpy.context.view_layer.update()
rec['rest_matched_deg'] = match; print('RESTMATCH', match)

# ---- relaxed hands: a light finger curl baked into the rest pose (the rig's fingers are otherwise straight in every clip)
CURL = {'01': 8, '02': 14, '03': 10}
bpy.context.view_layer.objects.active = rig
for pb in rig.pose.bones:
    for k, a in CURL.items():
        if pb.name.endswith(('_' + k + '_r', '_' + k + '_l')):
            pb.rotation_mode = 'XYZ'; pb.rotation_euler = (math.radians(a * (0.5 if pb.name.startswith('thumb') else 1)), 0, 0)
bpy.context.view_layer.update()
for o in parts.values():
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        if m.type == 'ARMATURE':
            name = m.name; bpy.ops.object.modifier_apply(modifier=name)
            mm = o.modifiers.new('Armature', 'ARMATURE'); mm.object = rig
bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='POSE'); bpy.ops.pose.armature_apply(selected=False); bpy.ops.object.mode_set(mode='OBJECT')
rec['finger_curl_deg'] = CURL

# ---- one skinned mesh
bpy.ops.object.select_all(action='DESELECT')
for o in parts.values(): o.select_set(True)
bpy.context.view_layer.objects.active = parts['Human']
bpy.ops.object.join()
char = bpy.context.view_layer.objects.active; char.name = 'char1'; char.data.name = 'char1'
for m in list(char.modifiers):
    if m.type == 'ARMATURE' and m.object != rig: char.modifiers.remove(m)
if not any(m.type == 'ARMATURE' for m in char.modifiers): bind(char, rig)
normalise(char)
rec['mesh'] = {'verts': len(char.data.vertices), 'tris': sum(len(p.vertices) - 2 for p in char.data.polygons), 'materials': [m.name for m in char.data.materials]}
print('CHAR', rec['mesh'])

# ---- retarget clips: world-space bind-pose delta (as CharacterFeelPass does in Unity)
CLIPS = {'idle': 'idle_252.glb', 'walk': 'basic_walking.glb', 'run': 'basic_running.glb'}
def rest_world(arm, name): return arm.matrix_world @ arm.data.bones[name].matrix_local
def retarget(clipname, path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before]
    src = next(o for o in new if o.type == 'ARMATURE')
    act = src.animation_data.action
    f0, f1 = [int(round(x)) for x in act.frame_range]
    names = [b.name for b in src.data.bones if b.name in rig.data.bones]
    order = [b.name for b in rig.data.bones]            # parents before children
    s_rest = {n: rest_world(src, n) for n in names}; t_rest = {b.name: rest_world(rig, b.name) for b in rig.data.bones}
    hip_ratio = t_rest['Hips'].translation.z / max(s_rest['Hips'].translation.z, 1e-6)
    tact = bpy.data.actions.new(clipname); rig.animation_data_create(); rig.animation_data.action = tact
    for pb in rig.pose.bones: pb.rotation_mode = 'QUATERNION'
    rinv = rig.matrix_world.inverted()
    sc = bpy.context.scene
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        sw = {n: src.matrix_world @ src.pose.bones[n].matrix for n in names}
        for pb in rig.pose.bones: pb.matrix_basis = Matrix.Identity(4)
        bpy.context.view_layer.update()
        for n in order:
            pb = rig.pose.bones[n]
            if n not in sw: continue
            rot = (sw[n].to_3x3().normalized() @ s_rest[n].to_3x3().normalized().inverted()) @ t_rest[n].to_3x3().normalized()
            cur = rig.matrix_world @ pb.matrix
            pos = cur.translation
            if n == 'Hips':
                d = sw[n].translation - s_rest[n].translation
                pos = t_rest[n].translation + d * hip_ratio
            pb.matrix = rinv @ (Matrix.Translation(pos) @ rot.to_4x4())
            bpy.context.view_layer.update()
            pb.keyframe_insert('rotation_quaternion', frame=f - f0)
            if n == 'Hips': pb.keyframe_insert('location', frame=f - f0)
    tr = rig.animation_data.nla_tracks.new(); tr.name = clipname
    st = tr.strips.new(clipname, 0, tact); rig.animation_data.action = None
    for pb in rig.pose.bones: pb.matrix_basis = Matrix.Identity(4)
    for o in new: bpy.data.objects.remove(o)
    rec.setdefault('clips', {})[clipname] = {'source': str(path.name), 'frames': f1 - f0 + 1, 'hip_ratio': round(hip_ratio, 4)}
    print('CLIP', clipname, f1 - f0 + 1)
if not NOANIM:
    for k, v in CLIPS.items(): retarget(k, MC / v)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'mpfb' / f'final_{TAG}.blend'))
(OUT / 'out').mkdir(exist_ok=True)
bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); char.select_set(True); bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.gltf(filepath=str(OUT / 'out' / 'colonist_mpfb.glb'), use_selection=True, export_format='GLB',
                          export_skins=True, export_animations=not NOANIM, export_animation_mode='NLA_TRACKS',
                          export_morph=False, export_yup=True, export_image_format='AUTO',
                          export_vertex_color='NAME', export_vertex_color_name='Col', export_all_vertex_colors=False,
                          export_tangents=True)
rec['glb_bytes'] = (OUT / 'out' / 'colonist_mpfb.glb').stat().st_size
(OUT / 'out' / 'colonist_mpfb.json').write_text(json.dumps(rec, indent=2))
if rig.animation_data:
    for t in rig.animation_data.nla_tracks: t.mute = True
render_views(str(OUT / 'mpfb' / f'final_{TAG}'), (0, 0, 0.9), 1.9, views=('front', 'quarter', 'side', 'back'), res=(450, 900))
hd = rig.matrix_world @ rig.data.bones['Head'].head_local
render_views(str(OUT / 'mpfb' / f'final_{TAG}_bust'), (hd.x, hd.y, hd.z - 0.04), 0.5, views=('front', 'quarter', 'side'), res=(500, 500))
render_views(str(OUT / 'mpfb' / f'final_{TAG}_eyes'), (hd.x, hd.y - 0.05, hd.z + 0.07), 0.12, views=('front',), res=(500, 500))
# a walk frame for a sanity check
if rig.animation_data and not NOANIM:
    rig.animation_data.action = bpy.data.actions['walk']; bpy.context.scene.frame_set(6)
    render_views(str(OUT / 'mpfb' / f'final_{TAG}_walk'), (0, 0, 0.9), 1.9, views=('side', 'front'), res=(450, 900))
    rig.animation_data.action = None
