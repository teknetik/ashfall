# servo/src/surface_view.py: look at the servo's OUTSIDE on the kit's fixed review rigs (kit/READY.md, 19:45 to 20:00:
# a white card of albedo 0.8 reads about 0.9 in scene-linear; the cards are in every frame), under the warm key and
# the neutral one, closed and opened, clean and as found, and beside the accepted alloy plates of the materials family.
# Written for the last surface pass (briefs/model-servo-surface.md); it changes nothing, it only renders.
#
#   SH/blender.sh servo/src/surface_view.py -- --src blend|glb [--dir export] --tag before --shots w_close,n_close,...
#                                              [--samples 20] [--res 1000x667] [--sheet 3]
#   --src blend : <dir>/servo.blend, the procedural materials (what a bake will be made from), any state
#   --src glb   : <dir>/servo.glb, the baked textures (what Unity gets); 'found' swaps in <dir>/tex/servo__dirty_*.png
# A shot is <rig>_<state>_<camera> or <rig>_<camera> (state clean):
#   rig    w = kit warm rig (3000 K key), n = kit neutral rig, l = the materials family's own bench lamp (2.4 W at
#          0.47 m, the light its accepted sheets were judged under)
#   state  clean | found | open (lid and its screws off, clips open) | plates (closed, with the two finished plates)
#   camera close, side (the -Y side it lay on), rear, front, top, bench (0.6 m), macro (the lid's shoulder, a crop of
#          the 0.3 m view), foot
# Writes review/surface/<tag>_<shot>.png and the sheet review/surface/<tag>.png.
import bpy, sys, os, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
SERVO = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(SERVO, '..', 'kit'))
import kitload
RV = kitload.load('review')
import mats as MT
import rig as RG
import contract as CT
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
opt = lambda k, d, cast=str: cast(argv[argv.index(k) + 1]) if k in argv else d
SRC = opt('--src', 'blend')
DIR = os.path.join(SERVO, opt('--dir', 'export'))
TAG = opt('--tag', 'view')
SHOTS = [s for s in opt('--shots', 'w_close,n_close').split(',') if s]
SPP = opt('--samples', 20, int)
RES = tuple(int(x) for x in opt('--res', '1000x667').split('x'))
COLS = opt('--sheet', 3, int)
OUT = os.path.join(SERVO, 'review', 'surface')
os.makedirs(OUT, exist_ok=True)

if SRC == 'glb':
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.join(DIR, 'servo.glb'))
    for o in list(bpy.data.objects):          # the importer's bone-shape meshes
        if o.type == 'MESH' and not o.name.startswith('servo_'):
            bpy.data.objects.remove(o)
    pj = json.load(open(os.path.join(DIR, 'parts.json')))
    P = {p['id']: bpy.data.objects[p['node']] for p in pj['parts']}
else:
    bpy.ops.wm.open_mainfile(filepath=os.path.join(DIR, 'servo.blend'))
    P = CT.parts('servo')
for o in list(bpy.data.objects):
    if o.type in ('CAMERA', 'LIGHT'):
        bpy.data.objects.remove(o)
sc = bpy.context.scene
f = 'servo.'
mats = [m for m in bpy.data.materials if m.use_nodes]
S_LID = [f + 'screw_case_' + k for k in 'abcd'] + [f + 'case_lid']
C = Vector((0, 0, 0.0275))
done, labels = {}, {}


# ---------------------------------------------------------------- lights
def set_rig(k, target=C):
    for o in list(bpy.data.objects):
        if o.type == 'LIGHT':
            bpy.data.objects.remove(o)
    for l in list(bpy.data.lights):
        bpy.data.lights.remove(l)
    RV.studio(samples=SPP, res=RES, warm=(k == 'w'))
    sc.render.image_settings.color_depth = '8'
    if k == 'l':        # materials/review.py warm(): one warm lamp above and behind the work, a dim warm room
        for o in list(bpy.data.objects):
            if o.type == 'LIGHT':
                bpy.data.objects.remove(o)
        w = bpy.data.worlds.new('warm_room'); w.use_nodes = True
        bg = w.node_tree.nodes['Background']
        bg.inputs[0].default_value = (0.9, 0.62, 0.38, 1); bg.inputs[1].default_value = 0.035
        sc.world = w
        ld = bpy.data.lights.new('warm', 'AREA'); ld.energy = 2.4; ld.color = (1.0, 0.71, 0.42); ld.size = 0.14
        lo = bpy.data.objects.new('light_warm', ld); sc.collection.objects.link(lo)
        off = Vector((0.10, 0.20, 0.42))
        lo.location = Vector(target) + off
        lo.rotation_euler = off.to_track_quat('Z', 'Y').to_euler()


# ---------------------------------------------------------------- states
DIRTY_MAT = {}


def glb_found(on):
    """GLB only: show the as-found texture set on the parts that have one (stats.json bake.dirty_objects)."""
    st = json.load(open(os.path.join(DIR, 'stats.json')))
    names = st.get('bake', {}).get('dirty_objects', [])
    for n in names:
        o = bpy.data.objects.get(n)
        if o is None:
            continue
        for s in o.material_slots:
            m = s.material
            if m is None:
                continue
            base = m.get('sv_clean_of') or m.name
            if on:
                if base not in DIRTY_MAT:
                    d = bpy.data.materials[base].copy(); d['sv_clean_of'] = base
                    for nd in d.node_tree.nodes:
                        if nd.type != 'TEX_IMAGE' or not nd.outputs['Color'].links:
                            continue
                        to = nd.outputs['Color'].links[0].to_node
                        kind = 'normal' if to.type == 'NORMAL_MAP' else ('color' if to.type == 'BSDF_PRINCIPLED' else 'orm')
                        im = bpy.data.images.load(os.path.join(DIR, 'tex', 'servo__dirty_%s.png' % kind), check_existing=True)
                        im.colorspace_settings.name = 'sRGB' if kind == 'color' else 'Non-Color'
                        nd.image = im
                    DIRTY_MAT[base] = d
                s.material = DIRTY_MAT[base]
            else:
                s.material = bpy.data.materials[base]


PLATES = []


def plates(on):
    """The two finished plates of the materials family (its baked GLB), paint up, in front of the servo."""
    if on and not PLATES:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=os.path.join(SERVO, '..', 'materials', 'export', 'materials.glb'))
        bpy.context.view_layer.update()
        names = [o.name for o in bpy.data.objects if o not in before]
        want = [n for n in names if n.split('.')[0] in ('materials_sheet_a_plate', 'materials_sheet_b_plate') and bpy.data.objects[n].type == 'MESH']
        print('PLATES found', want, 'of', len(names), 'imported objects', flush=True)
        for n in want:
            o = bpy.data.objects[n]
            mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
        for n in names:
            if n not in want and n in bpy.data.objects:
                bpy.data.objects.remove(bpy.data.objects[n])
        for n, (x, y, rz) in zip(sorted(want), ((-0.034, -0.098, 8), (0.036, -0.100, -6))):
            o = bpy.data.objects[n]
            o.matrix_world = Matrix.Rotation(math.radians(rz), 4, 'Z')
            bpy.context.view_layer.update()
            bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
            cx = sum(p.x for p in bb) / 8; cy = sum(p.y for p in bb) / 8; z0 = min(p.z for p in bb)
            o.matrix_world = Matrix.Translation((x - cx, y - cy, 0.0002 - z0)) @ o.matrix_world
            bpy.context.view_layer.update()
            print('PLATE', n, 'at', [round(v, 4) for v in o.matrix_world.translation], 'size', [round(v, 4) for v in o.dimensions], flush=True)
            PLATES.append(o)
    for o in PLATES:
        o.hide_render = not on


def state(st):
    found = st == 'found'
    opened = st == 'open'
    if SRC == 'glb':
        glb_found(found)
    else:
        MT.set_dirty(mats, 1.0 if found else 0.0)
        RG.set_params(bpy.data.objects['servo_rig'], {k: (1.0 if opened else 0.0) for k in ('clip_1', 'clip_2', 'clip_3')})
    for fid, o in P.items():
        o.hide_render = opened and fid in S_LID
    plates(st == 'plates')
    bpy.context.view_layer.update()


# ---------------------------------------------------------------- cameras
def cam(name, target, dist, down, yaw, fit=None):
    return RV.close_cam(Vector(target), dist=dist, down=down, lens=35.0, yaw=yaw, name=name, fit=fit)


CAMS = {
    'close': lambda n: cam(n, C, 0.30, 32, -60, 0.105),
    'side': lambda n: cam(n, C, 0.30, 12, -100, 0.105),
    'rear': lambda n: cam(n, C, 0.30, 28, 125, 0.105),
    'front': lambda n: cam(n, C, 0.30, 24, -128, 0.105),
    'top': lambda n: cam(n, C + Vector((0, 0, 0.02)), 0.30, 64, -80, 0.100),
    'bench': lambda n: RV.bench_cam(C, yaw=-70, name=n),
    'macro': lambda n: cam(n, Vector((0.006, -0.016, 0.046)), 0.30, 42, -78, 0.050),
    'foot': lambda n: cam(n, Vector((0.006, -0.026, 0.012)), 0.30, 20, -70, 0.060),
    'open': lambda n: cam(n, C + Vector((0.006, 0, 0.006)), 0.30, 48, -65, 0.100),
    'plates': lambda n: cam(n, Vector((0.002, -0.046, 0.012)), 0.30, 44, -78, 0.15),
}
RIGN = {'w': 'WARM key (kit rig)', 'n': 'neutral (kit rig)', 'l': 'materials bench lamp'}
ground = None
for rk in ('w', 'n', 'l'):
    mine = [s for s in SHOTS if s.split('_')[0] == rk]
    if not mine:
        continue
    set_rig(rk)
    if ground is None:
        ground = RV.ground(-0.0002, (0.028, 0.028, 0.03))
    for s in mine:
        bits = s.split('_')
        st, ck = ('clean', bits[1]) if len(bits) == 2 else (bits[1], bits[2])
        if st == 'open' and ck == 'close':
            ck = 'open'
        if ck == 'plates':          # 'w_plates' is the plates state (it parsed as clean until 21 Nov: no plates in frame)
            st = 'plates'
        if st == 'plates':
            ck = 'plates'
        state(st)
        done[s] = RV.render(os.path.join(OUT, '%s_%s.png' % (TAG, s)), CAMS[ck](s), RES, SPP)
        labels[s] = '%s %s: %s, %s, %s' % (TAG, SRC.upper(), st, ck, RIGN[rk])
        print('SHOT', s, flush=True)
RV.contact_sheet([done[s] for s in SHOTS if s in done], os.path.join(OUT, TAG + '.png'), cols=COLS, labels=[labels[s] for s in SHOTS if s in done], width=900)
print('SURFACE_VIEW', json.dumps(done))
