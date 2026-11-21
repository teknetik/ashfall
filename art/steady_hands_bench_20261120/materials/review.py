# materials/review.py: the review gate for the worked materials (CONTRACT.md "Review gate"): staged renders of the
# source scene (procedural materials, Cycles CPU) under the kit's neutral studio and under a warm work lamp
# (SEAM.md section 8), tiled beside sheets/materials_stock.png and the bench look target.
#   SH/blender.sh materials/review.py -- --only sheets,states,hero,leads,small [--samples 28]
import bpy, sys, os, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..', 'kit')))
import importlib.util
_spec = importlib.util.spec_from_file_location('kit_review', os.path.normpath(os.path.join(HERE, '..', 'kit', 'review.py')))
RV = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(RV)      # the kit's review, not this file
import mats as MT
import contract as CT
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
opt = lambda k, d, cast=str: cast(argv[argv.index(k) + 1]) if k in argv else d
ONLY = set(opt('--only', 'sheets,states,hero,leads,small').split(','))
SPP = opt('--samples', 28, int)
OUT = os.path.join(HERE, 'review')
MM = 0.001
GLB = '--glb' in argv          # look at the exported, baked GLB (what Unity gets) in place of the source scene
TAG = 'glb_' if GLB else ''
if GLB:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.join(HERE, 'export', 'materials.glb'))
else:
    bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'export', 'materials.blend'))
for o in list(bpy.data.objects):
    if o.type in ('CAMERA', 'LIGHT'):
        bpy.data.objects.remove(o)
RV.studio(samples=SPP)
sc = bpy.context.scene
pj = json.load(open(os.path.join(HERE, 'export', 'parts.json')))
P = {p['id']: bpy.data.objects[p['node']] for p in pj['parts']} if GLB else CT.parts('materials')
f = 'materials.'
mats = [m for m in bpy.data.materials if m.use_nodes]
ABSENT = set(pj['absent_at_start'])
ground = RV.ground(-0.0002, (0.030, 0.030, 0.032), size=3.0, rough=0.7)
done = {}
STUDIO_LIGHTS = [o for o in bpy.data.objects if o.type == 'LIGHT']
STUDIO_WORLD = sc.world
NEUTRAL_EV = 0.0        # the kit's neutral rig as it is since it was re-lit (PROGRESS.md 19:46: a white card reads 0.83 to 0.90). Before that it needed -1.6 EV.
# 'warm' below is this family's own lamp: 2.4 W area light 0.47 m above and behind the work, 3000 K, white = 0.9


def warm(target, on=True):
    sc.view_settings.exposure = 0.0 if on else NEUTRAL_EV
    """One warm work lamp above and behind the work, a dim warm room: the bench's light (about 3000 K)."""
    for o in STUDIO_LIGHTS:
        o.hide_render = on
    old = bpy.data.objects.get('light_warm')
    if old:
        bpy.data.objects.remove(old)
    if not on:
        sc.world = STUDIO_WORLD
        return
    w = bpy.data.worlds.get('warm_room') or bpy.data.worlds.new('warm_room')
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs[0].default_value = (0.9, 0.62, 0.38, 1); bg.inputs[1].default_value = 0.035
    sc.world = w
    ld = bpy.data.lights.new('warm', 'AREA'); ld.energy = 2.4; ld.color = (1.0, 0.71, 0.42); ld.size = 0.14
    lo = bpy.data.objects.new('light_warm', ld); sc.collection.objects.link(lo)
    off = Vector((0.10, 0.20, 0.42))
    lo.location = Vector(target) + off
    lo.rotation_euler = off.to_track_quat('Z', 'Y').to_euler()


def show(ids=None, hide=()):
    """ids: the part ids to show (short names); default = everything present at the start. hide: more to hide."""
    for fid, o in P.items():
        short = fid.split('.', 1)[1]
        vis = (fid not in ABSENT) if ids is None else (short in ids)
        o.hide_render = (not vis) or short in hide


SAVED = {fid: o.matrix_world.copy() for fid, o in P.items()}
ORDER = sorted(P, key=lambda fid: len(fid))       # parents before children is not guaranteed by length; restore twice


def move(short, M):
    o = P[f + short]
    kids = {c: c.matrix_world.copy() for c in o.children if c.type == 'MESH'}
    o.matrix_world = M
    bpy.context.view_layer.update()
    for c, m in kids.items():
        c.matrix_world = m
    bpy.context.view_layer.update()


def shift(short, d):
    o = P[f + short]
    M = o.matrix_world.copy(); M.translation = M.translation + Vector(d)
    move(short, M)


def restore():
    for _ in range(3):
        for fid, o in P.items():
            o.matrix_world = SAVED[fid]
        bpy.context.view_layer.update()


def cam(name, target, dist, down, yaw, fit=None, lens=35.0):
    return RV.close_cam(Vector(target), dist=dist, down=down, lens=lens, yaw=yaw, name=name, fit=fit)


def shot(name, c, res=(1200, 800)):
    done[name] = RV.render(os.path.join(OUT, TAG + name + '.png'), c, res, SPP)
    return done[name]


def sheet(name, keys, cols, labels):
    return RV.contact_sheet([done[k] for k in keys], os.path.join(OUT, TAG + name + '.png'), cols=cols, labels=[('GLB: ' if GLB else '') + l for l in labels], width=760)


SA_C = Vector((0.260, 0.0, 0.001)); SB_C = Vector((0.410, 0.0, 0.001)); BOTH = Vector((0.335, 0.0, 0.0))
A_KIDS = ['sheet_a', 'sheet_a_plate', 'sheet_a_margin', 'sheet_a_strap', 'sheet_a_offcut_1', 'sheet_a_offcut_2'] + ['sheet_a_plug_%d' % i for i in range(1, 5)]
B_KIDS = [k.replace('sheet_a', 'sheet_b') for k in A_KIDS]
ground.location.z = -0.0002

if 'sheets' in ONLY:
    MT.set_dirty(mats, 1.0)        # as found: no punch marks yet
    show(A_KIDS + B_KIDS)
    warm(BOTH, False)
    shot('a1_found_bench_neutral', RV.bench_cam(BOTH, yaw=-90))
    shot('a2_top_neutral', RV.look_cam('c_top', BOTH, (0, 0, 0.6), ortho=0.30), res=(1500, 560))
    warm(BOTH)
    shot('a3_found_bench_warm', RV.bench_cam(BOTH, yaw=-90))
    shot('a4_found_close_warm', cam('c4', SA_C, 0.30, 38, -72, fit=0.15))
    shot('a5_found_b_close_warm', cam('c5', SB_C, 0.30, 38, -108, fit=0.15))
    show(A_KIDS + ['sheet_a_scribe'])
    shot('a6_scribed_warm', cam('c6', SA_C + Vector((-0.02, 0.01, 0)), 0.30, 50, -80, fit=0.085))
    warm(BOTH, False)
    sheet('sheets', ['a1_found_bench_neutral', 'a3_found_bench_warm', 'a4_found_close_warm', 'a5_found_b_close_warm', 'a6_scribed_warm'], 3,
          ['as found, bench camera 0.6 m, neutral', 'the same, warm lamp', 'sheet A (paint up), 0.3 m, warm', 'sheet B (bare side up), 0.3 m, warm', 'scribed line, warm'])

if 'states' in ONLY:
    MT.set_dirty(mats, 0.0)
    # cut: the pieces a little apart, the plate with its sliver, punch marks made
    show(A_KIDS + ['swarf_%d' % i for i in range(1, 6)])
    shift('sheet_a_offcut_1', (-0.006, 0.008, 0)); shift('sheet_a_offcut_2', (0.008, 0.008, 0)); shift('sheet_a', (0, -0.008, 0))
    shift('sheet_a_strap', (0, -0.020, 0))
    for i in range(1, 6):
        shift('swarf_%d' % i, (-0.275, -0.050, 0))
    warm(SA_C)
    shot('b1_cut_warm', cam('b1', SA_C + Vector((-0.01, -0.012, 0)), 0.30, 46, -78, fit=0.16))
    # filed and drilled: no sliver, no plugs; the strap bent, lying on its edge
    show(['sheet_a', 'sheet_a_plate', 'sheet_a_offcut_1', 'sheet_a_offcut_2', 'strap_bent'] + ['swarf_%d' % i for i in range(1, 6)])
    move('strap_bent', Matrix.Translation((0.262, -0.055, 0.0085)) @ Matrix.Rotation(math.radians(200), 4, 'Z') @ Matrix.Translation((0.0, 0.03, 0.0)))
    shot('b2_finished_warm', cam('b2', SA_C + Vector((-0.01, -0.016, 0)), 0.30, 46, -78, fit=0.17))
    warm(SA_C, False)
    shot('b3_finished_neutral', cam('b3', SA_C + Vector((-0.01, -0.016, 0)), 0.30, 46, -78, fit=0.17))
    restore()
    sheet('states', ['b1_cut_warm', 'b2_finished_warm', 'b3_finished_neutral'], 3, ['cut (pieces apart), punched', 'filed, drilled, strap bent: warm', 'the same, neutral'])

if 'hero' in ONLY:
    # the finished pieces as the grip shows them: both plates paint up, the strap, at 0.3 m
    MT.set_dirty(mats, 0.0)
    show(['sheet_a_plate', 'sheet_b_plate', 'strap_bent', 'strap_bent_1', 'sheet_a_strap'])
    C = Vector((1.0, 0.0, 0.0))
    ground.location = (1.0, 0, -0.0002)
    move('sheet_a_plate', Matrix.Translation(C + Vector((-0.036, 0.0, 0.0))) @ Matrix.Rotation(math.radians(8), 4, 'Z'))
    move('sheet_b_plate', Matrix.Translation(C + Vector((0.036, 0.0, 0.0))) @ Matrix.Rotation(math.radians(-6), 4, 'Z'))
    move('strap_bent', Matrix.Translation(C + Vector((0.115, 0.045, 0.0085))) @ Matrix.Rotation(math.radians(180), 4, 'Z'))
    move('strap_bent_1', Matrix.Translation(C + Vector((-0.110, 0.055, 0.0085))) @ Matrix.Rotation(math.radians(160), 4, 'Z'))
    move('sheet_a_strap', Matrix.Translation(C + Vector((-0.06, -0.075, 0.0)) - Vector((0.200, -0.045, 0.0))) @ SAVED[f + 'sheet_a_strap'])
    warm(C)
    shot('h1_hero_warm', cam('h1', C + Vector((0.0, -0.01, 0.0)), 0.30, 52, -86, fit=0.19), res=(1500, 1000))
    shot('h2_plate_l_warm', cam('h2', C + Vector((-0.036, 0.0, 0.0)), 0.30, 58, -75, fit=0.085), res=(1000, 1100))
    shot('h3_strap_warm', cam('h3', C + Vector((0.085, 0.07, 0.006)), 0.30, 22, -55, fit=0.075))
    warm(C, False)
    shot('h4_hero_neutral', cam('h4', C + Vector((0.0, -0.01, 0.0)), 0.30, 52, -86, fit=0.19), res=(1500, 1000))
    shot('h5_low_neutral', cam('h5', C + Vector((0.0, 0.0, 0.0)), 0.30, 14, -100, fit=0.17))
    restore()
    ground.location = (0, 0, -0.0002)
    sheet('hero', ['h1_hero_warm', 'h4_hero_neutral', 'h2_plate_l_warm', 'h3_strap_warm', 'h5_low_neutral'], 3,
          ['plates L and R, strap flat / first bend / bent: warm', 'the same, neutral', 'left plate 0.3 m, warm', 'bent strap, warm', 'low angle (edges), neutral'])

if 'leads' in ONLY:
    # the unit from the servo family, standing on the bench in its own frame (the bench is 20 mm under the flange face)
    with bpy.data.libraries.load(os.path.join(HERE, '..', 'servo', 'export', 'servo.blend'), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n.startswith('servo_gimbal_') and '__' not in n]
    for o in dst.objects:
        sc.collection.objects.link(o)
    cr = bpy.data.objects['servo_gimbal_cradle']
    cr.parent = None
    cr.matrix_world = Matrix.Identity(4)
    bpy.context.view_layer.update()
    mats2 = [m for m in bpy.data.materials if m.use_nodes]
    MT.set_dirty(mats2, 0.0)
    ground.location = (0, 0, -0.0202)
    T0 = Vector((0.0, 0.022, -0.010))
    LA = ['lead_a', 'lead_b', 'lead_sense'] + [x % k for k in 'ab' for x in ('lead_%s_slug', 'lead_%s_strands', 'lead_%s_offcut')]
    warm(T0)
    show(LA)
    shot('l1_as_cut_warm', cam('l1', T0 + Vector((0, 0.008, 0)), 0.30, 40, -150, fit=0.085))
    MT.set_dirty(mats2, 1.0)       # stripped, not yet tinned
    show(['lead_a', 'lead_b', 'lead_a_strands', 'lead_b_strands', 'lead_a_slug', 'sleeve_a', 'sleeve_b'])
    shift('lead_a_slug', (bpy.data.objects['materials_lead_a_slug__clear'].matrix_world.translation - SAVED[f + 'lead_a_slug'].translation) * 0.6)
    shot('l2_stripped_warm', cam('l2', T0 + Vector((0, 0.006, -0.003)), 0.30, 38, 150, fit=0.050))
    restore()
    MT.set_dirty(mats2, 0.0)
    show(['lead_a', 'lead_b', 'lead_a_strands', 'lead_b_strands', 'sleeve_a', 'sleeve_b'])
    shot('l3_tinned_warm', cam('l3', T0 + Vector((0, 0.006, -0.003)), 0.30, 38, 150, fit=0.050))
    show(['loop_lead_a', 'loop_lead_b', 'loop_resistor', 'loop_sleeve_a', 'loop_sleeve_b'])
    shot('l4_loop_warm', cam('l4', T0 + Vector((0, -0.004, 0.004)), 0.30, 40, -150, fit=0.062))
    warm(T0, False)
    shot('l5_loop_neutral', cam('l5', T0 + Vector((0, -0.002, 0.002)), 0.30, 24, 62, fit=0.058))
    show(['loop_tucked'])
    shot('l6_tucked_neutral', cam('l6', T0 + Vector((0, -0.006, 0.008)), 0.30, 78, -90, fit=0.058))
    for o in dst.objects:
        o.hide_render = True
    ground.location = (0, 0, -0.0002)
    sheet('leads', ['l1_as_cut_warm', 'l2_stripped_warm', 'l3_tinned_warm', 'l4_loop_warm', 'l5_loop_neutral', 'l6_tucked_neutral'], 3,
          ['as cut (bands, offcuts, sense lead)', 'trimmed, stripped (one slug sliding off), sleeves on', 'tinned', 'loop soldered, sleeves shrunk: warm', 'the same, low, neutral',
           'tucked on the interface line (top view)'])

if 'small' in ONLY:
    MT.set_dirty(mats, 1.0)
    C = Vector((1.0, 0.5, 0.0))
    ground.location = (1.0, 0.5, -0.0002)
    show(['vial', 'vial_fluid', 'vial_stopper', 'vial_line', 'bobbin', 'bobbin_wire', 'resistor', 'sleeve_a'] + ['swarf_%d' % i for i in range(1, 6)])
    P[f + 'bobbin_wire'].hide_render = True
    for short, pos in (('vial', (-0.03, 0.0, 0)), ('bobbin', (0.025, 0.012, 0)), ('resistor', (-0.004, -0.032, 0))):
        o = P[f + short]
        M = SAVED[f + short].copy(); M.translation = C + Vector(pos)
        kids = [c for c in o.children if c.type == 'MESH']
        rel = {c: SAVED[f + short].inverted() @ c.matrix_world for c in kids}
        o.matrix_world = M
        bpy.context.view_layer.update()
        for c in kids:
            c.matrix_world = M @ rel[c]
    bpy.context.view_layer.update()
    for i in range(1, 6):
        shift('swarf_%d' % i, C + Vector((0.045, -0.03, 0)) - Vector((0.506, 0.0, 0)))
    P[f + 'sleeve_a'].hide_render = True
    warm(C)
    shot('s1_small_warm', cam('s1', C + Vector((0.005, -0.004, 0.022)), 0.30, 30, -82, fit=0.105))
    shot('s2_vial_warm', cam('s2', C + Vector((-0.03, 0.0, 0.034)), 0.30, 18, -70, fit=0.074), res=(800, 1100))
    warm(C, False)
    shot('s3_small_neutral', cam('s3', C + Vector((0.005, -0.004, 0.022)), 0.30, 30, -82, fit=0.105))
    P[f + 'bobbin_wire'].hide_render = False
    P[f + 'vial_stopper'].hide_render = True
    MT.set_dirty(mats, 0.0)
    shot('s4_wound_open_neutral', cam('s4', C + Vector((0.0, 0.0, 0.03)), 0.30, 42, -82, fit=0.10))
    shot('s5_resistor_swarf_warm_off', cam('s5', C + Vector((0.02, -0.031, 0.001)), 0.30, 40, -90, fit=0.06))
    restore()
    ground.location = (0, 0, -0.0002)
    sheet('small', ['s1_small_warm', 's3_small_neutral', 's2_vial_warm', 's4_wound_open_neutral', 's5_resistor_swarf_warm_off'], 3,
          ['vial, empty bobbin, resistor, swarf: warm', 'the same, neutral', 'vial, warm', 'bobbin wound, vial open (legs tinned)', 'resistor and swarf, neutral'])

if 'ev' in ONLY:
    # for the record: the same plates under the kit's two rigs as they are, and under the neutral rig at -1.6 EV
    MT.set_dirty(mats, 0.0)
    show(['sheet_a_plate', 'sheet_b_plate'])
    C = Vector((1.0, 0.0, 0.0))
    ground.location = (1.0, 0, -0.0002)
    move('sheet_a_plate', Matrix.Translation(C + Vector((-0.036, 0.0, 0.0))) @ Matrix.Rotation(math.radians(8), 4, 'Z'))
    move('sheet_b_plate', Matrix.Translation(C + Vector((0.036, 0.0, 0.0))) @ Matrix.Rotation(math.radians(-6), 4, 'Z'))
    c_ = cam('e1', C, 0.30, 52, -86, fit=0.13)
    warm(C, False)
    for o in STUDIO_LIGHTS:
        o.location = o.location + C
    sc.view_settings.exposure = 0.0
    shot('e1_kit_neutral_ev0', c_, res=(900, 600))
    sc.view_settings.exposure = NEUTRAL_EV
    shot('e2_kit_neutral_ev-1.6', c_, res=(900, 600))
    for o in STUDIO_LIGHTS:
        bpy.data.objects.remove(o)
    RV.studio(samples=SPP, warm=True)
    for o in [o for o in bpy.data.objects if o.type == 'LIGHT']:
        o.location = o.location + C
    sc.view_settings.exposure = 0.0
    shot('e3_kit_warm_ev0', c_, res=(900, 600))
    sc.view_settings.exposure = -2.2
    shot('e4_kit_warm_ev-2.2', c_, res=(900, 600))
    sheet('exposure_ab', ['e1_kit_neutral_ev0', 'e2_kit_neutral_ev-1.6', 'e3_kit_warm_ev0', 'e4_kit_warm_ev-2.2'], 2,
          ['kit neutral rig as it is (EV 0)', 'kit neutral rig, -1.6 EV', 'kit warm rig as it is (EV 0)', 'kit warm rig, -2.2 EV'])
    restore()

if 'core' in ONLY:
    # the pressed core (grip family) with its flash and sprue, as the mould opens
    with bpy.data.libraries.load(os.path.join(HERE, '..', 'grip', 'export', 'grip.blend'), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n == 'grip_core']
    gc = dst.objects[0]
    sc.collection.objects.link(gc)
    bpy.context.view_layer.update()
    MT.set_dirty([m for m in bpy.data.materials if m.use_nodes], 0.0)
    ids = [p['id'].split('.', 1)[1] for p in pj['parts'] if p['id'].startswith('materials.core_')]
    show(ids)
    lo = min((gc.matrix_world @ v.co).z for v in gc.data.vertices)
    CC = gc.matrix_world @ (sum((v.co for v in gc.data.vertices), Vector()) / len(gc.data.vertices))
    ground.location = (CC.x, CC.y, lo - 0.02)
    ground.hide_render = True
    warm(CC, False)
    shot('c1_core_side_neutral', cam('k1', CC, 0.30, 4, -90, fit=0.135))
    shot('c2_core_base_neutral', cam('k2', CC + Vector((0.01, 0, -0.045)), 0.30, -32, -55, fit=0.075))
    shot('c3_core_top_neutral', cam('k3', CC + Vector((-0.02, 0, 0.04)), 0.30, 38, -140, fit=0.085))
    warm(CC)
    shot('c4_core_right_warm', cam('k4', CC, 0.30, 18, 78, fit=0.135))
    warm(CC, False)
    gc.hide_render = True
    ground.hide_render = False
    sheet('core', ['c1_core_side_neutral', 'c2_core_base_neutral', 'c3_core_top_neutral', 'c4_core_right_warm'], 4,
          ['pressed core with flash and sprue, left side: neutral', 'base and sprue from below: neutral', 'top (no fin across the tang slot): neutral', 'right side: warm'])

print('REVIEW', json.dumps(done))
