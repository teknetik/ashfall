# servo/review.py: the review gate for the servo family (CONTRACT.md "Review gate"): staged renders of the source
# scene (procedural materials, Cycles CPU) beside the reference sheets.
#   SH/blender.sh servo/review.py [-- --only states,close,exploded,gimbal --samples 24]
# Writes review/*.png and the sheets review/compare_exploded.png, compare_close.png, states.png, gimbal.png.
import bpy, sys, os, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'kit'))
import review as RV
import mats as MT
import rig as RG
import contract as CT
import measure as ME
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
opt = lambda k, d, cast=str: cast(argv[argv.index(k) + 1]) if k in argv else d
ONLY = set(opt('--only', 'states,close,exploded,gimbal').split(','))
SPP = opt('--samples', 24, int)
OUT = os.path.join(HERE, 'review')
MM = 0.001
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'export', 'servo.blend'))
for o in list(bpy.data.objects):
    if o.type in ('CAMERA', 'LIGHT'):
        bpy.data.objects.remove(o)
RV.studio(samples=SPP)


def warm(on):
    """The kit's calibrated rigs (kit/READY.md, fixed 19:45 on 20 Nov: a white card of albedo 0.8 reads about 0.9 in
    scene-linear): on = the bench's one warm work lamp, about 3000 K; off = the neutral studio. Until 21 Nov this
    recoloured the neutral rig by hand, which is not the calibrated warm rig."""
    for o in list(bpy.data.objects):
        if o.type == 'LIGHT':
            bpy.data.objects.remove(o)
    for l in list(bpy.data.lights):
        bpy.data.lights.remove(l)
    RV.studio(samples=SPP, warm=bool(on))


P = CT.parts('servo')
f = 'servo.'
mats = [m for m in bpy.data.materials if m.use_nodes]
clip = bpy.data.objects['servo_rig']; gim = bpy.data.objects['servo_gimbal_rig']
ground = RV.ground(-0.0002, (0.028, 0.028, 0.03))
GIMBAL = [x for x in P if x.startswith(f + 'gimbal_')]
LEADS = [f + 'lead_coil_a', f + 'lead_coil_b', f + 'lead_sense']
done = {}


def show(hidden=(), only=None):
    for fid, o in P.items():
        o.hide_render = (fid in hidden) if only is None else (fid not in only)


def cam(name, target, dist, down, yaw, fit=None, lens=35.0):
    return RV.close_cam(Vector(target), dist=dist, down=down, lens=lens, yaw=yaw, name=name, fit=fit)


def shot(name, c, res=(1200, 800)):
    done[name] = RV.render(os.path.join(OUT, name + '.png'), c, res, SPP)
    return done[name]


C = Vector((0, 0, 0.0275))
S_SCREWS = [f + 'screw_case_' + k for k in 'abcd']
S_LID = S_SCREWS + [f + 'case_lid']
S_BOARD = S_LID + [f + 'lead_plug', f + 'trim_resistor', f + 'board']
S_GEARS = S_BOARD + [f + 'circlip', f + 'gear_top', f + 'gear_mid', f + 'gear_low']
gc = P[f + 'gimbal_cradle'].matrix_world.translation.copy()

if 'preview' in ONLY:        # a quick look at the surfaces before a bake
    MT.set_dirty(mats, 0.0); show()
    shot('p2_dusted', cam('p2', C, 0.30, 32, -60, fit=0.105), res=(1000, 667))
    shot('p5_side', cam('p5', C, 0.30, 12, -100, fit=0.105), res=(1000, 667))
    warm(True)
    shot('p3_dusted_warm', cam('p3', C, 0.30, 32, -60, fit=0.105), res=(1000, 667))
    warm(False)
    RV.contact_sheet([done[k] for k in ('p2_dusted', 'p5_side', 'p3_dusted_warm')], os.path.join(OUT, 'preview.png'), cols=3,
                     labels=['dusted (neutral)', 'dusted, the side it lay on (neutral)', 'dusted, warm key'])

if 'states' in ONLY:          # warm (the calibrated bench lamp) and neutral panels, cards in every frame (21 Nov)
    show()
    for rig, k in ((True, 'w'), (False, 'n')):
        warm(rig)
        MT.set_dirty(mats, 1.0)
        shot('s0%s_found_bench' % k, RV.bench_cam(C, yaw=-70))
        shot('s1%s_found_close' % k, cam('c1' + k, C, 0.30, 32, -60, fit=0.105))
        MT.set_dirty(mats, 0.0)
        shot('s2%s_clean_close' % k, cam('c2' + k, C, 0.30, 32, -60, fit=0.105))
    warm(True)
    MT.set_dirty(mats, 1.0)
    shot('s1bw_found_rear', cam('c1b', C, 0.30, 28, 125, fit=0.105))
    MT.set_dirty(mats, 0.0)
    shot('s2sw_clean_side', cam('c2s', C, 0.30, 12, -100, fit=0.105))
    RG.set_params(clip, {'clip_1': 1.0, 'clip_2': 1.0, 'clip_3': 1.0}); show(S_LID)
    shot('s3_lid_off', cam('c3', C + Vector((0.006, 0, 0.006)), 0.30, 48, -65, fit=0.100))
    show(S_BOARD)
    shot('s4_board_off', cam('c4', C + Vector((0.006, 0, 0.004)), 0.30, 52, -65, fit=0.092))
    show(S_GEARS)
    MT.set_dirty(mats, 1.0)
    shot('s5_gears_off', cam('c5', C + Vector((0.008, 0, 0.002)), 0.30, 56, -65, fit=0.085))
    show(S_GEARS + GIMBAL + LEADS + [f + 'screw_trunnion_a', f + 'screw_trunnion_b'])
    shot('s6_gimbal_out', cam('c6', C + Vector((0.008, 0, 0.0)), 0.30, 58, -65, fit=0.085))
    RG.set_params(clip, {'clip_1': 0.0, 'clip_2': 0.0, 'clip_3': 0.0}); MT.set_dirty(mats, 0.0); show(); warm(False)
    keys = ['s0w_found_bench', 's1w_found_close', 's2w_clean_close', 's0n_found_bench', 's1n_found_close', 's2n_clean_close',
            's1bw_found_rear', 's2sw_clean_side', 's3_lid_off', 's4_board_off', 's5_gears_off', 's6_gimbal_out']
    RV.contact_sheet([done[k] for k in keys], os.path.join(OUT, 'states.png'), cols=3,
                     labels=['as found, bench camera 0.6 m, WARM key (kit rig)', 'as found, 0.3 m, WARM', 'clean set, 0.3 m, WARM',
                             'as found, bench camera 0.6 m, neutral (kit rig)', 'as found, 0.3 m, neutral', 'clean set, 0.3 m, neutral',
                             'as found, rear, WARM', 'clean set, the -Y side it lay on, WARM', 'lid off, WARM', 'board off, WARM',
                             'gears off (gimbal as found), WARM', 'gimbal out, WARM'])

if 'gimbal' in ONLY:
    ground.hide_render = True
    show(only=GIMBAL + LEADS)
    MT.set_dirty(mats, 1.0)
    shot('g1_found_3q', cam('g1', gc + Vector((0, 0, -0.008)), 0.30, 42, -125, fit=0.046))
    MT.set_dirty(mats, 0.0)
    shot('g2_clean_3q', cam('g2', gc + Vector((0, 0, -0.008)), 0.30, 42, -125, fit=0.046))
    show(only=GIMBAL)
    shot('g3_side', cam('g3', gc + Vector((0, 0, -0.010)), 0.30, 2, -90, fit=0.040))
    shot('g4_top', cam('g4', gc + Vector((0, 0, -0.004)), 0.30, 88, -90, fit=0.036))
    RG.set_params(gim, {'gimbal_pitch': 1.0, 'gimbal_roll': 0.0})
    shot('g5_tilted', cam('g5', gc + Vector((0, 0, -0.004)), 0.30, 62, -125, fit=0.038))
    RG.set_params(gim, {'gimbal_pitch': 0.5, 'gimbal_roll': 0.5})
    # the unit taken apart along its own axis: retaining ring, rotor, race, ring, coil above the cradle
    up = (P[f + 'gimbal_cradle'].matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
    saved = {}
    for fid, d in ((f + 'gimbal_coil', 0.030), (f + 'gimbal_ring', 0.042), (f + 'gimbal_race', 0.054), (f + 'gimbal_rotor', 0.074), (f + 'gimbal_retainer', 0.090),
                   (f + 'gimbal_grit_1', 0.056), (f + 'gimbal_grit_2', 0.056), (f + 'gimbal_grit_3', 0.056)):
        o = P[fid]; saved[fid] = o.matrix_world.copy()
        m = o.matrix_world.copy(); m.translation = m.translation + up * d; o.matrix_world = m
    bpy.context.view_layer.update()
    shot('g6_apart', cam('g6', gc + Vector((0, 0, 0.034)), 0.42, 14, -115, fit=0.125), res=(900, 1350))
    for fid, m in saved.items():
        P[fid].matrix_world = m
    bpy.context.view_layer.update()
    ground.hide_render = False
    RV.contact_sheet([done[k] for k in ('g1_found_3q', 'g2_clean_3q', 'g3_side', 'g4_top', 'g5_tilted')], os.path.join(OUT, 'gimbal.png'), cols=3,
                     labels=['as found (corrosion, grit)', 'cleaned', 'side: body d 26 x 18, flange d 30 x 2', 'top', 'pitch 1.0, roll 0.0 (both stops)'])

if 'close' in ONLY:
    # the six panels of sheets/servo_close1.png: gimbal 3/4, gimbal side, board, gear stack, lid corner, front bell
    ground.hide_render = True
    MT.set_dirty(mats, 1.0)
    show(only=GIMBAL + LEADS)
    shot('k1_gimbal', cam('k1', gc + Vector((0, 0, -0.008)), 0.30, 40, -130, fit=0.048))
    show(only=GIMBAL)
    shot('k2_gimbal_side', cam('k2', gc + Vector((0, 0, -0.010)), 0.30, 4, -90, fit=0.042))
    MT.set_dirty(mats, 0.0)
    show(only=[f + 'board', f + 'trim_resistor', f + 'lead_plug'])
    shot('k3_board', cam('k3', Vector((0.006, -0.002, 0.045)), 0.30, 78, -90, fit=0.072))
    show(only=[f + 'gear_low', f + 'gear_mid', f + 'gear_top', f + 'circlip', f + 'output_shaft'])
    shot('k4_gears', cam('k4', Vector((-0.009, 0.0, 0.034)), 0.30, 38, -55, fit=0.040))
    MT.set_dirty(mats, 1.0); show()
    shot('k5_lid_corner', cam('k5', Vector((0.026, 0.030, 0.031)), 0.30, 30, 62, fit=0.030))
    shot('k6_front_bell', cam('k6', Vector((-0.036, 0.0, 0.029)), 0.30, 16, -152, fit=0.062))
    MT.set_dirty(mats, 0.0)
    ground.hide_render = False
    sheet = RV.contact_sheet([done[k] for k in ('k1_gimbal', 'k2_gimbal_side', 'k3_board', 'k4_gears', 'k5_lid_corner', 'k6_front_bell')], os.path.join(OUT, 'close_sheet.png'), cols=3,
                             labels=['gimbal (as found)', 'gimbal, side', 'board, resistor, plug', 'gear stack and shaft', 'lid corner (as found)', 'front bell (as found)'])
    RV.beside(os.path.join(HERE, 'sheets', 'servo_close1.png'), sheet, os.path.join(OUT, 'compare_close.png'), height=1400)

if 'exploded' in ONLY:
    ground.hide_render = True
    show(); MT.set_dirty(mats, 0.0)
    RG.set_params(clip, {'clip_1': 1.0, 'clip_2': 1.0, 'clip_3': 1.0})
    objs = list(P.values())
    up = Vector((0, 0, 1))
    # heights (m) for a readable stack, like the exploded sheet: lid highest, then screws, board, plug, circlip, gears, gimbal
    lift = {'case_lid': 0.088, 'screw_case_a': 0.064, 'screw_case_b': 0.064, 'screw_case_c': 0.064, 'screw_case_d': 0.064, 'board': 0.046, 'lead_plug': 0.050,
            'trim_resistor': 0.056, 'circlip': 0.046, 'gear_top': 0.037, 'gear_mid': 0.029, 'gear_low': 0.021, 'screw_trunnion_a': 0.018, 'screw_trunnion_b': 0.018,
            'gimbal_cradle': 0.0}
    side = {'gimbal_cradle': Vector((0.062, -0.010, -0.010)), 'lead_plug': Vector((0.0, -0.030, 0.0))}
    kids = {}
    for fid, o in P.items():
        par = json.loads(o['sh']).get('parent')
        kids.setdefault(par, []).append(fid)

    def tree(fid):
        r = [fid]
        for c in kids.get(fid, []):
            r += tree(c)
        return r
    saved = {fid: o.matrix_world.copy() for fid, o in P.items()}
    moved = set()
    for short, dz in lift.items():
        off = up * dz + side.get(short, Vector((0, 0, 0)))
        for fid in tree(f + short):
            if fid in moved:
                continue
            moved.add(fid)
            o = P[fid]; m = saved[fid].copy(); m.translation = m.translation + off; o.matrix_world = m
            bpy.context.view_layer.update()         # a child set before its parent has moved would move twice
    # the unit itself taken apart in a row, as on the sheet: coil, ring, race, rotor, retaining ring
    row = {'gimbal_coil': 0.032, 'gimbal_ring': 0.058, 'gimbal_race': 0.082, 'gimbal_grit_1': 0.082, 'gimbal_grit_2': 0.082, 'gimbal_grit_3': 0.082,
           'gimbal_rotor': 0.104, 'gimbal_retainer': 0.122}
    for short, dx in row.items():
        o = P[f + short]; m = o.matrix_world.copy(); m.translation = m.translation + Vector((dx, 0, 0.012)); o.matrix_world = m
        bpy.context.view_layer.update()
    bpy.context.view_layer.update()
    lo, hi = ME.bounds(objs)
    c2 = Vector((lo + hi) / 2); e2 = float(max(hi - lo))
    shot('x1_exploded', RV.look_cam('cam_x1', c2, Vector((-0.22, -0.95, 0.48)).normalized() * 0.80, lens=100), res=(1500, 1000))
    shot('x2_exploded_side', RV.look_cam('cam_x2', c2, (0, -0.8, 0), ortho=e2 * 1.08), res=(1500, 1000))
    for fid in sorted(saved, key=lambda x: len(tree(x)), reverse=True):
        P[fid].matrix_world = saved[fid]
        bpy.context.view_layer.update()
    RG.set_params(clip, {'clip_1': 0.0, 'clip_2': 0.0, 'clip_3': 0.0})
    sheet = RV.contact_sheet([done['x1_exploded'], done['x2_exploded_side']], os.path.join(OUT, 'exploded_sheet.png'), cols=1, labels=['exploded', 'exploded, side (orthographic)'])
    RV.beside(os.path.join(HERE, 'sheets', 'servo_exploded.png'), sheet, os.path.join(OUT, 'compare_exploded.png'), height=1200)
print('REVIEW', json.dumps(done))
