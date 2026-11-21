# render_holds.py: the pistol held at the fixtures' pose marks, to look at (model-bench).
#   SH/blender.sh fixtures/src/render_holds.py [-- --only vise,mat,cradle] [--samples 24]
# The fixtures come from export/fixtures.blend (the rig is live, so the vise closes to the value check.json found), the
# pistol from ../pistol/export/pistol.glb at rest, moved so that its frame node takes the mark's pose. Cards and the
# power cell are hidden for the vise and the cradle (the cell is on the pad by then). Kit warm rig.
# Out: review/hold_<name>.png (bench camera, front above, side, top) for each hold.
import bpy, os, sys, json, math
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools', 'src'))
import mbk
from mbk import PROG, LAYOUT, RG
import review as RV

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ONLY = argv[argv.index('--only') + 1].split(',') if '--only' in argv else None
SAMPLES = int(argv[argv.index('--samples') + 1]) if '--samples' in argv else 24
FDIR = os.path.join(PROG, 'fixtures')
OUT = os.path.join(FDIR, 'review')
CK = json.load(open(os.path.join(FDIR, 'export', 'check.json')))
JAW = {r['mark']: r['jaw'] for r in (CK.get('rests') or {}).get('rests', []) if r.get('jaw') is not None}

bpy.ops.wm.open_mainfile(filepath=os.path.join(FDIR, 'export', 'fixtures.blend'))
for o in list(bpy.data.objects):
    if o.type in ('CAMERA', 'LIGHT'):
        bpy.data.objects.remove(o)
RV.WARM = True
sc = RV.studio(samples=SAMPLES, res=(1100, 760))
mbk.rest_all()
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=os.path.join(PROG, 'pistol', 'export', 'pistol.glb'))
PIS = [o for o in bpy.data.objects if o not in before]
for o in PIS:
    if o.animation_data:
        o.animation_data_clear()
    if o.type == 'ARMATURE':
        for pb in o.pose.bones:
            pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
bpy.context.view_layer.update()
ROOTS = [o for o in PIS if o.parent is None]
HOME = {o.name: o.matrix_world.copy() for o in ROOTS}
frame = bpy.data.objects['pistol_frame']
F0 = frame.matrix_world.copy()
arm = bpy.data.objects.get('fixtures_vise_rig')

# name: (owner node, mark, pistol nodes hidden, jaw value or None, what to frame)
HOLDS = {
    'vise': ('fixtures_vise', 'seat_work', ('pistol_card_a', 'pistol_card_b', 'pistol_cell'), JAW.get('seat_work'), 'fixtures_vise'),
    'mat': ('fixtures_workmat', 'seat_pistol', ('pistol_card_a', 'pistol_card_b'), None, 'fixtures_workmat'),
    'cradle': ('fixtures_cradle', 'seat_frame', ('pistol_card_a', 'pistol_card_b', 'pistol_cell'), None, 'fixtures_cradle'),
}


def hidden(o, names):
    while o is not None:
        if o.name in names:
            return True
        o = o.parent
    return False


def bounds(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for o in objs:
        if o.type != 'MESH' or o.hide_render:
            continue
        oe = o.evaluated_get(dg)
        for c in oe.bound_box:
            p = oe.matrix_world @ Vector(c)
            lo = Vector((min(lo.x, p.x), min(lo.y, p.y), min(lo.z, p.z))); hi = Vector((max(hi.x, p.x), max(hi.y, p.y), max(hi.z, p.z)))
    return lo, hi


g = RV.ground(-0.0003, (0.05, 0.048, 0.045))
cam_b = LAYOUT['camera']
e = math.radians(cam_b['pitch_down_deg'])
for name, (owner, mark, hide, jaw, focus) in HOLDS.items():
    if ONLY and name not in ONLY:
        continue
    me = bpy.data.objects.get('%s__mark_%s' % (owner, mark))
    if me is None:
        print('HOLD skip', name, 'no mark'); continue
    if arm is not None:
        RG.set_params(arm, {'vise_jaw': float(jaw) if jaw is not None else 0.0})
    bpy.context.view_layer.update()
    M = me.matrix_world @ F0.inverted()
    for o in ROOTS:
        o.matrix_world = M @ HOME[o.name]
    for o in PIS:
        o.hide_render = hidden(o, hide) or (o.type == 'MESH' and not o.name.startswith('pistol_'))     # Blender's importer adds an 'Icosphere' bone-shape mesh
    bpy.context.view_layer.update()
    lo, hi = bounds([o for o in PIS if o.name.startswith('pistol_')] + [o for o in bpy.data.objects if o.name == focus or o.name.startswith(focus + '_')])
    c = (lo + hi) / 2; ext = max(hi - lo)
    cams = [('bench camera', RV._cam('h_bench', cam_b['eye'], (0, math.cos(e), -math.sin(e)), (0, 0, 1), lens=cam_b['lens_mm'])),
            ('from in front and above', RV.close_cam(c, dist=0.55, down=40, yaw=-90, name='h_front', fit=ext)),
            ('from the left', RV.look_cam('h_side', c, (-0.8, 0, 0), ortho=ext * 1.25)),
            ('from above', RV.look_cam('h_top', c, (0, 0, 0.8), ortho=ext * 1.25))]
    paths, labels = [], []
    for n, cam in cams:
        p = os.path.join(OUT, '_hold_%s_%s.png' % (name, n.replace(' ', '_')))
        RV.render(p, cam, res=(1500, 844) if n == 'bench camera' else (1100, 760)); paths.append(p); labels.append('%s: %s' % (name, n) + (' (jaw %.3f)' % jaw if jaw is not None else ''))
    RV.contact_sheet(paths, os.path.join(OUT, 'hold_%s.png' % name), cols=2, labels=labels, width=950)
    for p in paths:
        os.remove(p)
    for n, cam in cams:
        bpy.data.objects.remove(cam)
    # which pistol parts are between the pads, and how high the grip parts stand over the jaw tops
    if name == 'vise':
        body = bpy.data.objects['fixtures_vise']; Bi = body.matrix_world.inverted()
        rep = {}
        for o in PIS:
            if o.type != 'MESH' or o.hide_render or not o.name.startswith('pistol_'):
                continue
            pts = [Bi @ (o.matrix_world @ v.co) for v in o.data.vertices]
            zs = [p.z for p in pts]
            inpad = sum(1 for p in pts if abs(p.x) <= 0.042 and 0.1095 <= p.z <= 0.1356)
            rep[o.name] = {'z_mm': [round(min(zs) * 1000, 1), round(max(zs) * 1000, 1)], 'x_mm': [round(min(p.x for p in pts) * 1000, 1), round(max(p.x for p in pts) * 1000, 1)],
                           'verts_between_pads': inpad}
        json.dump({'jaw': jaw, 'jaw_top_z_mm': 135.6, 'pad_z_mm': [109.5, 135.6], 'pad_half_width_mm': 42.0, 'parts': rep},
                  open(os.path.join(OUT, 'hold_vise.json'), 'w'), indent=1)
        for k, v in sorted(rep.items(), key=lambda kv: -kv[1]['verts_between_pads'])[:40]:
            print('HOLD vise', k, v, flush=True)
    print('HOLD done', name, flush=True)
if arm is not None:
    RG.set_params(arm, {'vise_jaw': 0.0})
print('HOLDS DONE')
